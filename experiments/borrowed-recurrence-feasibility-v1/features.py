"""Fixed acoustic features for completed one-second windows at 24 kHz.

No output from this module is available before the entire input window arrives
and its computation finishes. MERT's bidirectional context spans that completed
window: the ten pooled rows are descriptions of its time bins, NOT ten causal
inner-frame outputs. The caller records arrival and computation timestamps.

Chroma L1 normalization and quantization follow the CENS construction described
by Mueller, Kurth and Clausen (WASPAA 2005), as explained in the primary FMP
notebook: https://www.audiolabs-erlangen.de/resources/MIR/FMP/C7/C7S2_CENS.html
The fixed FFT front below is an explicit experimental variant, not the original
filterbank. Temporal smoothing and subsequent L2 normalization belong to the
caller; this module never applies centered smoothing or accesses other audio.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time

import numpy as np


SAMPLE_RATE = 24000
WINDOW_SAMPLES = 24000
FRAME_SAMPLES = 2400
FFT_SIZE = 4096
PITCHES = np.arange(24, 105, dtype=np.int64)
_HANN = np.hanning(FRAME_SAMPLES).astype(np.float64)
_WINDOW_ENERGY = float(np.dot(_HANN, _HANN))
_FREQUENCIES = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)
_NEAREST_MIDI = np.full(_FREQUENCIES.shape, -1, dtype=np.int64)
_POSITIVE = _FREQUENCIES > 0
_NEAREST_MIDI[_POSITIVE] = np.floor(
    69.0 + 12.0 * np.log2(_FREQUENCIES[_POSITIVE] / 440.0) + 0.5
).astype(np.int64)
_IN_RANGE = (_NEAREST_MIDI >= 24) & (_NEAREST_MIDI <= 104)
_PITCH_BIN = _NEAREST_MIDI[_IN_RANGE] - 24
_THRESHOLDS = np.array([0.05, 0.1, 0.2, 0.4], dtype=np.float64)


def _pcm(pcm: np.ndarray) -> np.ndarray:
    x = np.asarray(pcm)
    if x.shape != (WINDOW_SAMPLES,) or x.dtype != np.float32:
        raise ValueError("Expected exactly 24000 mono float32 samples at 24000 Hz")
    if not np.isfinite(x).all():
        raise ValueError("PCM must contain only finite samples")
    return x


def spectral(pcm: np.ndarray) -> dict[str, np.ndarray]:
    """Return absolute spectral power, unwindowed RMS, and quantized chroma.

    Each row describes one non-overlapping 2400-sample frame. A symmetric Hann
    window precedes the zero-padded 4096-point real FFT. One-sided bin power is
    |FFT|**2 / (4096 * sum(Hann**2)), doubled except DC/Nyquist. Thus summing all
    FFT bins gives window-weighted mean-square amplitude (Parseval); the returned
    81 bins retain only centers nearest MIDI 24..104. Their amplitudes have no
    per-frame normalization, logarithmic compression, or learned transformation.

    RMS is calculated from all 2400 unwindowed samples. Pitch-class powers are
    L1-normalized then quantized with inclusive lower thresholds .05/.1/.2/.4.
    Exact silence remains zero. Chroma is float32 with values 0..4, before any
    caller-owned smoothing/L2 normalization.
    """
    frames = _pcm(pcm).astype(np.float64).reshape(10, FRAME_SAMPLES)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    fft = np.fft.rfft(frames * _HANN, n=FFT_SIZE, axis=1)
    fft_power = (fft.real * fft.real + fft.imag * fft.imag)
    fft_power /= FFT_SIZE * _WINDOW_ENERGY
    fft_power[:, 1:-1] *= 2.0
    power = np.stack([
        np.bincount(_PITCH_BIN, weights=row[_IN_RANGE], minlength=81)
        for row in fft_power
    ])
    chroma_power = np.stack([
        np.sum(power[:, PITCHES % 12 == pitch_class], axis=1)
        for pitch_class in range(12)
    ], axis=1)
    total = np.sum(chroma_power, axis=1, keepdims=True)
    distribution = np.divide(
        chroma_power, total, out=np.zeros_like(chroma_power), where=total > 0
    )
    chroma = np.searchsorted(_THRESHOLDS, distribution, side="right").astype(np.float32)
    return {"power": power, "rms": rms, "chroma": chroma}


def _duration_pool(rows: np.ndarray) -> np.ndarray:
    """Integrate uniformly spaced hidden rows over ten equal-duration bins.

    Native hidden rows are treated as piecewise constant over equal durations
    covering the completed window. Fractional overlaps, not integer slicing,
    determine weights. This is a pooling convention, not a claim about exact
    convolutional receptive fields or individual row availability times.
    """
    values = np.asarray(rows, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] != 768:
        raise ValueError("Expected nonempty hidden rows with 768 dimensions")
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite MERT hidden state")
    count = values.shape[0]
    native_left = np.arange(count, dtype=np.float64)
    native_right = native_left + 1.0
    target_edges = np.linspace(0.0, float(count), 11)
    overlap = np.maximum(
        0.0,
        np.minimum(target_edges[1:, None], native_right[None, :])
        - np.maximum(target_edges[:-1, None], native_left[None, :]),
    )
    overlap /= np.diff(target_edges)[:, None]
    pooled = (overlap @ values).astype(np.float32)
    if pooled.shape != (10, 768) or not np.isfinite(pooled).all():
        raise ValueError("Invalid pooled MERT features")
    return pooled


class MertFeatures:
    """Frozen, local-only compatible HuBERT load used by the preparation probe.

    ``extract`` returns ``{'layer6': (10,768), 'layer12': (10,768)}``.
    Model hidden-state indexing counts the embedding output as zero, so these
    are the outputs after encoder layers six and twelve. No hidden state or PCM
    is retained between calls. ``metadata`` and ``weights_hashes`` describe the
    fixed resource; ``last_compute_seconds`` describes the most recent call.
    """

    def __init__(self, model_dir: str | Path, cache_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.cache_dir = Path(cache_dir)
        if not self.model_dir.is_dir():
            raise FileNotFoundError(self.model_dir)
        os.environ.update(
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HOME=str(self.cache_dir),
            HF_HUB_DISABLE_TELEMETRY="1",
        )
        import torch
        from transformers import HubertConfig, HubertModel, Wav2Vec2FeatureExtractor

        self._torch = torch
        torch.set_num_threads(4)
        torch.manual_seed(20260922)
        cfg = json.loads((self.model_dir / "config.json").read_text())
        if not (
            cfg["feature_extractor_cqt"] is False
            and cfg["deepnorm"] is False
            and cfg["attention_relax"] == -1
            and cfg["feat_proj_layer_norm"] is True
            and cfg["hidden_size"] == 768
            and cfg["num_hidden_layers"] == 12
        ):
            raise ValueError("Local MERT configuration differs from qualified HuBERT compatibility")
        self.weights_hashes = {}
        for name in ("config.json", "preprocessor_config.json", "pytorch_model.bin"):
            with (self.model_dir / name).open("rb") as source:
                self.weights_hashes[name] = hashlib.file_digest(source, "sha256").hexdigest()
        started = time.perf_counter()
        self.model = HubertModel(HubertConfig.from_dict(cfg)).to("cpu")
        state = torch.load(
            self.model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True
        )
        keys = self.model.load_state_dict(state, strict=True)
        del state
        self.model.eval().requires_grad_(False)
        self.processor = Wav2Vec2FeatureExtractor.from_pretrained(
            str(self.model_dir), local_files_only=True
        )
        if self.processor.sampling_rate != SAMPLE_RATE:
            raise ValueError("Qualified MERT processor requires 24000 Hz")
        if any(parameter.requires_grad for parameter in self.model.parameters()):
            raise RuntimeError("MERT parameters must remain frozen")
        self.last_compute_seconds = None
        self.metadata = {
            "model_class": type(self.model).__name__,
            "device": "cpu",
            "threads": torch.get_num_threads(),
            "sample_rate": SAMPLE_RATE,
            "window_samples": WINDOW_SAMPLES,
            "layers": [6, 12],
            "native_layer_index_zero": "embedding output",
            "pooled_shape_per_layer": [10, 768],
            "pooling": "fractional equal-duration overlap of uniformly spaced hidden rows",
            "parameters": sum(p.numel() for p in self.model.parameters()),
            "trainable_parameters": 0,
            "missing_keys": list(keys.missing_keys),
            "unexpected_keys": list(keys.unexpected_keys),
            "model_hashes": dict(self.weights_hashes),
            "versions": {name: importlib.metadata.version(name)
                         for name in ("numpy", "torch", "transformers")},
            "load_seconds": time.perf_counter() - started,
            "output_availability": "All 24000 samples arrived, then complete inference and pooling; all ten rows share this availability",
            "retained_audio_between_calls": False,
            "external_downloads": False,
        }

    def extract(self, pcm: np.ndarray) -> dict[str, np.ndarray]:
        x = _pcm(pcm)
        started = time.perf_counter()
        inputs = self.processor(
            x, sampling_rate=SAMPLE_RATE, return_tensors="pt"
        ).input_values.to("cpu")
        with self._torch.inference_mode():
            output = self.model(inputs, output_hidden_states=True)
        if len(output.hidden_states) != 13:
            raise RuntimeError("Expected embedding plus twelve encoder states")
        features = {
            f"layer{layer}": _duration_pool(output.hidden_states[layer][0].cpu().numpy())
            for layer in (6, 12)
        }
        self.last_compute_seconds = time.perf_counter() - started
        return features
