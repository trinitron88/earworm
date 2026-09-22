"""Offline qualification only: one two-second non-evaluation sine fixture.

No music study, readout selection, persistent memory or causal claim is made.
The model sees the complete fixture; outputs become available after inference.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import time

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--cache-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  HF_HOME=str(a.cache_dir), HF_HUB_DISABLE_TELEMETRY='1')
started = time.perf_counter()
import numpy as np
import torch
from transformers import HubertConfig, HubertModel, Wav2Vec2FeatureExtractor

torch.set_num_threads(4)
torch.manual_seed(20260922)
cfg = json.loads((a.model_dir / 'config.json').read_text())
assert cfg['feature_extractor_cqt'] is False
assert cfg['deepnorm'] is False and cfg['attention_relax'] == -1
assert cfg['feat_proj_layer_norm'] is True
load_started = time.perf_counter()
model = HubertModel(HubertConfig.from_dict(cfg))
state = torch.load(a.model_dir / 'pytorch_model.bin', map_location='cpu', weights_only=True)
keys = model.load_state_dict(state, strict=True)
del state
model.eval().requires_grad_(False)
processor = Wav2Vec2FeatureExtractor.from_pretrained(a.model_dir, local_files_only=True)
load_seconds = time.perf_counter() - load_started
assert processor.sampling_rate == 24000
samples = 48000
pcm = (0.1 * np.sin(2 * np.pi * 440 * np.arange(samples) / 24000)).astype(np.float32)
inference_started = time.perf_counter()
inputs = processor(pcm, sampling_rate=24000, return_tensors='pt').input_values
with torch.inference_mode():
    out = model(inputs, output_hidden_states=True)
inference_seconds = time.perf_counter() - inference_started
assert all(torch.isfinite(h).all() for h in out.hidden_states)
assert all(not param.requires_grad for param in model.parameters())
hashes = {}
for name in ['config.json', 'preprocessor_config.json', 'pytorch_model.bin']:
    with (a.model_dir / name).open('rb') as f:
        hashes[name] = hashlib.file_digest(f, 'sha256').hexdigest()
report = dict(status='runtime_probe_pass', scope='non-evaluation runtime qualification only',
              route_session_probes=1, fixture_seconds=2, sample_rate=24000,
              model_class=type(model).__name__, device='cpu', threads=4,
              parameters=sum(x.numel() for x in model.parameters()),
              trainable_parameters=0, missing_keys=keys.missing_keys,
              unexpected_keys=keys.unexpected_keys, model_hashes=hashes,
              versions={x: importlib.metadata.version(x) for x in ['torch','transformers','numpy','scipy']},
              hidden_shapes=[list(h.shape) for h in out.hidden_states],
              load_seconds=load_seconds, inference_seconds=inference_seconds,
              qualification_elapsed_seconds=time.perf_counter()-started,
              peak_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              output_availability='After all 48000 samples and complete inference; no streaming latency claim',
              confirms_comparison_resource_feasibility=False, external_spending=0)
a.output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
