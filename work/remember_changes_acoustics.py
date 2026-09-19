"""Experiment 05: waveform-only pitch identity plus an acoustic change record.

All functions consume only a completed waveform block or its stored description.
They do not consume note metadata, edit labels, trial labels, or future blocks.
The pitch tracker assumes a clear monophonic fundamental. It is not a general
speech/polyphonic pitch tracker. Analytic phase refinement has finite bandwidth;
event edge and low-amplitude measurements are excluded rather than interpreted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt, stft


PARAMETERS = {
    "version": 1,
    "old_sample_rate": 16000, "old_window_s": .064, "old_hop_s": .010, "old_nfft": 8192,
    "old_peak_range_hz": [80., 1200.], "old_voicing_relative_power": .08,
    "new_window_s": .020, "new_hop_s": .005, "new_nfft": 16384,
    "new_peak_range_hz": [70., 1400.], "new_voicing_relative_power": .08,
    "event_envelope_window_s": .005, "event_grid_s": .001,
    "event_relative_rms_threshold": .10, "event_min_duration_s": .025,
    "event_max_internal_gap_s": .010, "event_pitch_edge_exclusion_s": .018,
    "phase_bandpass_order": 6, "phase_bandpass_f0_factors": [.65, 1.45],
    "phase_frequency_smoothing_s": .001,
    "event_match_gap_cost": 1.2, "event_match_pitch_scale_semitones": 2.,
    "event_match_normalized_timing_weight": .20,
    "bins": 32,
    "parameter_selection": "Fixed physical extraction and matching constants before access to Experiment05 held-out audio; no fitting to edit metadata.",
}


def equal_bins(sequence, bins=32):
    """Mean over equal-duration output bins, splitting boundary frames by area.

    Input rows are uniformly spaced piecewise-constant frame values. Integration
    is in float64; stored output is float32. Handles fewer input rows than bins.
    This preserves the global mean and commutes with time reversal, unlike
    np.array_split followed by unweighted bin averaging when lengths differ.
    """
    values = np.asarray(sequence)
    if values.ndim < 1 or len(values) == 0 or not isinstance(bins, int) or bins < 1:
        raise ValueError("Need a nonempty sequence and a positive integer bin count.")
    if not np.isfinite(values).all():
        raise ValueError("equal_bins requires finite values; retain masks separately.")
    n = len(values)
    values = values.astype(np.float64)
    prefix = np.concatenate([np.zeros_like(values[:1]), np.cumsum(values, axis=0)])
    edges = np.linspace(0., float(n), bins + 1)
    left = np.floor(edges).astype(int)
    shape = (bins + 1,) + (1,) * (values.ndim - 1)
    integral = prefix[left] + (edges - left).reshape(shape) * values[np.minimum(left, n - 1)]
    return (np.diff(integral, axis=0) / (n / bins)).astype(np.float32)


def _spectral_track(audio, sr, window_s, hop_s, nfft, allowed_hz, relative_power):
    window = round(window_s * sr)
    hop = round(hop_s * sr)
    f, times, spectrum = stft(audio, fs=sr, nperseg=window, noverlap=window-hop,
                              nfft=max(nfft, window), boundary=None, padded=False)
    power = np.abs(spectrum).astype(np.float64) ** 2
    energy = power.sum(axis=0)
    voiced = energy > max(float(energy.max()) * relative_power, 1e-10)
    possible = np.flatnonzero((f >= allowed_hz[0]) & (f <= min(allowed_hz[1], sr / 2 - sr / max(nfft, window))))
    if not len(possible):
        raise ValueError("Sample rate does not support the configured pitch range.")
    peaks = possible[np.argmax(power[possible], axis=0)]
    logp = np.log(power + 1e-15)
    ii = np.arange(len(peaks))
    left, middle, right = logp[peaks-1, ii], logp[peaks, ii], logp[peaks+1, ii]
    denom = left - 2*middle + right
    offset = np.divide(.5*(left-right), denom, out=np.zeros_like(denom), where=np.abs(denom)>1e-10)
    frequency = (peaks + np.clip(offset, -.5, .5)) * sr / max(nfft, window)
    centroid = np.divide((power * f[:, None]).sum(0), energy, out=np.zeros_like(energy), where=energy>1e-14)
    return times, frequency, voiced, centroid, energy


def _runs(mask):
    changes = np.diff(np.r_[False, mask, False].astype(np.int8))
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def _events(audio, sr):
    envelope = np.sqrt(np.maximum(uniform_filter1d(audio.astype(np.float64)**2,
                                size=max(1, round(PARAMETERS["event_envelope_window_s"]*sr)),
                                mode="constant"), 0))
    stride = max(1, round(PARAMETERS["event_grid_s"]*sr))
    sampled = envelope[::stride]
    mask = sampled > max(float(sampled.max()) * PARAMETERS["event_relative_rms_threshold"], 1e-5)
    for start, end in _runs(~mask):
        if start > 0 and end < len(mask) and (end-start)*stride/sr <= PARAMETERS["event_max_internal_gap_s"]:
            mask[start:end] = True
    events = [(start*stride/sr, min(end*stride/sr, len(audio)/sr)) for start, end in _runs(mask)
              if (end-start)*stride/sr >= PARAMETERS["event_min_duration_s"]]
    return events


def describe_audio(audio: np.ndarray, sr: int) -> dict:
    """Describe only the provided completed block. No supplied event boundaries."""
    audio = np.ascontiguousarray(audio, dtype=np.float32)
    if audio.ndim != 1 or len(audio) < round(.100*sr) or not np.isfinite(audio).all():
        raise ValueError("Expected a finite mono waveform at least 100 ms long.")
    if sr < 4000:
        raise ValueError("Sample rate must be at least 4 kHz.")
    from math import gcd
    common = gcd(sr, PARAMETERS["old_sample_rate"])
    old_audio = resample_poly(audio, PARAMETERS["old_sample_rate"]//common, sr//common).astype(np.float32) if sr != PARAMETERS["old_sample_rate"] else audio
    old_t, old_hz, old_voiced, _, _ = _spectral_track(old_audio, PARAMETERS["old_sample_rate"], PARAMETERS["old_window_s"],
        PARAMETERS["old_hop_s"], PARAMETERS["old_nfft"], PARAMETERS["old_peak_range_hz"], PARAMETERS["old_voicing_relative_power"])
    old_pitch = (12*np.log2(old_hz[old_voiced]/220.)).astype(np.float32)[:, None]
    has_pitch = len(old_pitch) > 0
    if has_pitch:
        corrected = equal_bins(old_pitch)
        center = float(corrected.astype(np.float64).mean())
        legacy = np.stack([chunk.mean(axis=0) for chunk in np.array_split(old_pitch, 32)]).astype(np.float32) if len(old_pitch) >= 32 else corrected.copy()
    else:
        corrected = np.zeros((32, 1), np.float32); legacy = corrected.copy(); center = float("nan")
    times, frequency, voiced, centroid, _ = _spectral_track(audio, sr, PARAMETERS["new_window_s"],
        PARAMETERS["new_hop_s"], PARAMETERS["new_nfft"], PARAMETERS["new_peak_range_hz"], PARAMETERS["new_voicing_relative_power"])
    sample_indices = np.minimum(np.round(times*sr).astype(int), len(audio)-1)
    rms_all = np.sqrt(np.maximum(uniform_filter1d(audio.astype(np.float64)**2,
                        size=round(PARAMETERS["new_window_s"]*sr), mode="constant"), 0))
    rms = rms_all[sample_indices]
    refined = frequency.copy()
    phase_mask = np.zeros(len(times), bool)
    events = _events(audio, sr)
    event_pitch, event_bend, event_span, event_quality = [], [], [], []
    for onset, offset in events:
        interior = (times >= onset + PARAMETERS["event_pitch_edge_exclusion_s"]) & (times <= offset - PARAMETERS["event_pitch_edge_exclusion_s"]) & voiced
        if interior.sum() < 3:
            event_pitch.append(np.nan); event_bend.append(np.nan); event_span.append(np.nan); event_quality.append(0.)
            continue
        rough = float(np.median(frequency[interior]))
        low, high = np.asarray(PARAMETERS["phase_bandpass_f0_factors"])*rough
        low = max(low, 20.); high = min(high, sr*.45)
        sos = butter(PARAMETERS["phase_bandpass_order"], [low, high], btype="bandpass", fs=sr, output="sos")
        filtered = sosfiltfilt(sos, audio.astype(np.float64))
        analytic = hilbert(filtered)
        angle = np.unwrap(np.angle(analytic))
        inst = np.gradient(angle)*sr/(2*np.pi)
        inst = gaussian_filter1d(inst, sigma=max(.5, PARAMETERS["phase_frequency_smoothing_s"]*sr), mode="nearest")
        amplitude = np.abs(analytic)
        event_samples = (np.arange(len(audio))/sr >= onset) & (np.arange(len(audio))/sr <= offset)
        amp_floor = max(float(amplitude[event_samples].max())*.10, 1e-7)
        valid_phase = interior & (amplitude[sample_indices] > amp_floor) & (inst[sample_indices] > rough*.65) & (inst[sample_indices] < rough*1.45)
        refined[valid_phase] = inst[sample_indices[valid_phase]]
        phase_mask[valid_phase] = True
        trace = 12*np.log2(refined[interior]/220.)
        baseline = float(np.median(trace))
        residual = (trace-baseline)*100
        # A signed extremum preserves whether a bend is upward or downward.
        peak = float(residual[np.argmax(np.abs(residual))])
        event_pitch.append(baseline); event_bend.append(peak)
        event_span.append(float(np.max(trace)-np.min(trace))*100)
        event_quality.append(float(valid_phase.sum()/interior.sum()))
    frame_pitch = np.where(voiced, refined, np.nan)
    result = {
        "sample_rate": int(sr), "duration_s": float(len(audio)/sr), "has_pitch": bool(has_pitch),
        "pitch_32": corrected, "relative_pitch_32": (corrected-center).astype(np.float32) if has_pitch else corrected.copy(),
        "absolute_pitch_center": center, "legacy_pitch_32": legacy, "pitch_voiced_64ms": old_pitch,
        "old_frame_time_s": old_t.astype(np.float32), "old_frame_voiced": old_voiced,
        "frame_time_s": times.astype(np.float32), "frame_rms": rms.astype(np.float32),
        "frame_energy_dbfs": (20*np.log10(np.maximum(rms, 1e-8))).astype(np.float32),
        "frame_voiced": voiced, "frame_pitch_hz": frame_pitch.astype(np.float32),
        "frame_spectral_peak_hz": np.where(voiced, frequency, np.nan).astype(np.float32),
        "frame_phase_refined": phase_mask, "frame_spectral_centroid_hz": centroid.astype(np.float32),
        "event_onset_s": np.asarray([e[0] for e in events], np.float32),
        "event_offset_s": np.asarray([e[1] for e in events], np.float32),
        "event_pitch_semitones": np.asarray(event_pitch, np.float32),
        "event_bend_peak_cents": np.asarray(event_bend, np.float32),
        "event_pitch_span_cents": np.asarray(event_span, np.float32),
        "event_phase_fraction": np.asarray(event_quality, np.float32),
    }
    return result


def _align_events(ref, query):
    """Monotonic sequence alignment, with gaps and robust global nuisance shifts."""
    rp = np.asarray(ref["event_pitch_semitones"], float); qp = np.asarray(query["event_pitch_semitones"], float)
    rt = np.asarray(ref["event_onset_s"], float); qt = np.asarray(query["event_onset_s"], float)
    if not len(rp) or not len(qp) or not np.isfinite(rp).all() or not np.isfinite(qp).all():
        return [], list(range(len(rp))), list(range(len(qp))), float("inf")
    # Every observed pair supplies a possible global pitch shift. Candidate
    # selection depends only on measured audio events, never on edit labels.
    shifts = np.unique(np.round((qp[:, None]-rp[None, :]).ravel(), 2))
    best = None
    for shift in shifts:
        pitch_cost = np.minimum(np.abs(qp[None, :]-rp[:, None]-shift)/PARAMETERS["event_match_pitch_scale_semitones"], 3.)
        # Elapsed timing is deliberately a weak alignment cue: a missing first
        # event should be alignable without assuming the starts correspond.
        normalized_rt = (rt-rt[0])/max(rt[-1]-rt[0], .01)
        normalized_qt = (qt-qt[0])/max(qt[-1]-qt[0], .01)
        cost = pitch_cost + PARAMETERS["event_match_normalized_timing_weight"]*np.abs(normalized_rt[:, None]-normalized_qt[None, :])
        n,m = cost.shape; dp=np.full((n+1,m+1),np.inf); previous=np.zeros((n+1,m+1),np.int8); dp[0,0]=0
        gap=PARAMETERS["event_match_gap_cost"]
        dp[:,0]=np.arange(n+1)*gap; dp[0,:]=np.arange(m+1)*gap
        for i in range(1,n+1):
            for j in range(1,m+1):
                choices=(dp[i-1,j-1]+cost[i-1,j-1],dp[i-1,j]+gap,dp[i,j-1]+gap)
                move=int(np.argmin(choices));dp[i,j]=choices[move];previous[i,j]=move
        matched=[]; omitted=[]; inserted=[]; i=n;j=m
        while i or j:
            move=previous[i,j] if i and j else (1 if i else 2)
            if move==0:matched.append((i-1,j-1));i-=1;j-=1
            elif move==1:omitted.append(i-1);i-=1
            else:inserted.append(j-1);j-=1
        matched.reverse();omitted.reverse();inserted.reverse()
        candidate=(float(dp[n,m]),-len(matched),abs(float(shift)),matched,omitted,inserted)
        if best is None or candidate[:3]<best[:3]: best=candidate
    return best[3],best[4],best[5],best[0]


def recover_changes(ref_desc: dict, query_desc: dict) -> dict:
    """Recover observed acoustic changes, independently of perceptual identity.

    Onsets are absolute block-relative measurements. timing_residual_s removes a
    robust affine timing fit, while onset_shift_s keeps the original difference.
    tempo_ratio > 1 means faster (reciprocal of onset-spacing scale).
    """
    matched, omitted, inserted, alignment_cost = _align_events(ref_desc, query_desc)
    pairs=np.asarray(matched,int).reshape(-1,2)
    result={"valid":bool(len(pairs)>=2),"matched_event_indices":pairs,
        "omitted_reference_positions":np.asarray(omitted,np.int32),"inserted_query_positions":np.asarray(inserted,np.int32),
        "alignment_cost":alignment_cost,"global_pitch_shift_semitones":float("nan"),"tempo_ratio":float("nan"),
        "timing_scale":float("nan"),"timing_offset_s":float("nan"),
        "event_timing_resolution_s":PARAMETERS["event_grid_s"],"pitch_analysis_hop_s":PARAMETERS["new_hop_s"],
        "pitch_bandwidth_warning":"Phase-refined monophonic estimate; brief bends can be smoothed and event-edge pitch is excluded."}
    if not len(pairs):
        for key in ("per_note_pitch_change_cents","absolute_note_pitch_change_cents","pitch_bend_change_cents","onset_shift_s","offset_shift_s","timing_residual_s","duration_ratio"):
            result[key]=np.zeros(0,np.float32)
        return result
    ri,qi=pairs.T
    rp=np.asarray(ref_desc["event_pitch_semitones"],float)[ri];qp=np.asarray(query_desc["event_pitch_semitones"],float)[qi]
    rt=np.asarray(ref_desc["event_onset_s"],float)[ri];qt=np.asarray(query_desc["event_onset_s"],float)[qi]
    re=np.asarray(ref_desc["event_offset_s"],float)[ri];qe=np.asarray(query_desc["event_offset_s"],float)[qi]
    shift=float(np.median(qp-rp))
    slopes=[(qt[j]-qt[i])/(rt[j]-rt[i]) for i in range(len(rt)) for j in range(i+1,len(rt)) if rt[j]-rt[i]>.025]
    scale=float(np.median(slopes)) if slopes else 1.
    intercept=float(np.median(qt-scale*rt))
    result.update(global_pitch_shift_semitones=shift,tempo_ratio=1/scale if scale>0 else float("nan"),
        timing_scale=scale,timing_offset_s=intercept,
        absolute_note_pitch_change_cents=((qp-rp)*100).astype(np.float32),
        per_note_pitch_change_cents=((qp-rp-shift)*100).astype(np.float32),
        pitch_bend_change_cents=(np.asarray(query_desc["event_bend_peak_cents"])[qi]-np.asarray(ref_desc["event_bend_peak_cents"])[ri]).astype(np.float32),
        onset_shift_s=(qt-rt).astype(np.float32),offset_shift_s=(qe-re).astype(np.float32),
        timing_residual_s=(qt-(scale*rt+intercept)).astype(np.float32),
        duration_ratio=((qe-qt)/np.maximum(re-rt,1e-6)).astype(np.float32))
    return result


def freeze_parameters(path=None):
    path=Path(path) if path else Path(__file__).with_name("remember_changes_acoustics_parameters.json")
    content=json.dumps(PARAMETERS,indent=2,sort_keys=True)+"\n"
    if path.exists() and path.read_text()!=content:
        raise RuntimeError("A parameter freeze already exists with different contents.")
    path.write_text(content)
    return hashlib.sha256(content.encode()).hexdigest()


if __name__ == "__main__":
    print(json.dumps({"parameter_sha256":freeze_parameters(),"parameters":PARAMETERS},indent=2))
