"""Experiment06: monotonic matching of incomplete waveform-derived event traces.

The matcher receives only inferred event pitches and block-relative onsets. A
global pitch shift and affine elapsed-time transform are nuisance parameters.
Dynamic-programming alignment retains explicit costs for skipped reference and
query events. It does not select a memory, set a decision threshold, or assign
perceptual identity; those are separate evaluation responsibilities.

Constants were chosen before any Experiment06 audio inspection. Gap cost and
pitch scale are inherited from Experiment05. Small fixed dead zones prevent
sub-resolution acoustic estimation differences from breaking a score tie.
"""
from __future__ import annotations

import numpy as np


PARAMETERS = {
    "version": 1,
    "gap_penalty": 1.2,
    "pitch_scale_semitones": 2.,
    "pitch_deadzone_semitones": .05,
    "timing_scale_s": .100,
    "timing_deadzone_s": .005,
    "timing_weight": .20,
    "proposal_normalized_time_weight": .20,
    "shift_hypothesis_round_decimals": 2,
    "refinement_passes": 1,
    "minimum_matched_events": 2,
    "numerical_tie_tolerance": 1e-12,
    "unavailable_score": -1e6,
    "normalization": "divide total loss by max(reference event count, query event count)",
    "selection": "Fixed before Experiment06 audio access; no learned parameters or metadata inputs.",
}


def _read(description):
    pitch = np.asarray(description["event_pitch_semitones"], dtype=np.float64)
    onset = np.asarray(description["event_onset_s"], dtype=np.float64)
    valid = (pitch.ndim == onset.ndim == 1 and len(pitch) == len(onset)
             and len(pitch) >= PARAMETERS["minimum_matched_events"]
             and np.isfinite(pitch).all() and np.isfinite(onset).all()
             and np.all(np.diff(onset) > 0))
    return pitch, onset, bool(valid)


def _deadzone(values, width):
    return np.maximum(np.abs(values) - width, 0.)


def _align(cost):
    """Global monotonic alignment with substitution, deletion, and insertion."""
    n, m = cost.shape
    gap = PARAMETERS["gap_penalty"]
    cumulative = np.full((n + 1, m + 1), np.inf)
    previous = np.zeros((n + 1, m + 1), dtype=np.int8)
    cumulative[:, 0] = np.arange(n + 1) * gap
    cumulative[0, :] = np.arange(m + 1) * gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            options = (cumulative[i - 1, j - 1] + cost[i - 1, j - 1],
                       cumulative[i - 1, j] + gap, cumulative[i, j - 1] + gap)
            move = int(np.argmin(options))
            cumulative[i, j] = options[move]
            previous[i, j] = move
    pairs, omitted, inserted = [], [], []
    i, j = n, m
    while i or j:
        move = int(previous[i, j]) if i and j else (1 if i else 2)
        if move == 0:
            pairs.append((i - 1, j - 1)); i -= 1; j -= 1
        elif move == 1:
            omitted.append(i - 1); i -= 1
        else:
            inserted.append(j - 1); j -= 1
    return pairs[::-1], omitted[::-1], inserted[::-1]


def _fit_and_measure(rp, rt, qp, qt, alignment):
    pairs, omitted, inserted = alignment
    if len(pairs) < PARAMETERS["minimum_matched_events"]:
        return None
    ri, qi = np.asarray(pairs, int).T
    shift = float(np.median(qp[qi] - rp[ri]))
    # A median of all pairwise slopes is robust to an isolated onset shift.
    # Measured monotonic onsets keep every slope positive.
    slopes = [(qt[qi[j]] - qt[qi[i]]) / (rt[ri[j]] - rt[ri[i]])
              for i in range(len(ri)) for j in range(i + 1, len(ri))]
    scale = float(np.median(slopes))
    offset = float(np.median(qt[qi] - scale * rt[ri]))
    pitch_residual = qp[qi] - rp[ri] - shift
    time_residual = qt[qi] - (scale * rt[ri] + offset)
    pitch_loss = float(_deadzone(pitch_residual, PARAMETERS["pitch_deadzone_semitones"]).sum()
                       / PARAMETERS["pitch_scale_semitones"])
    timing_loss = float(PARAMETERS["timing_weight"]
                        * _deadzone(time_residual, PARAMETERS["timing_deadzone_s"]).sum()
                        / PARAMETERS["timing_scale_s"])
    gap_loss = PARAMETERS["gap_penalty"] * (len(omitted) + len(inserted))
    total = pitch_loss + timing_loss + gap_loss
    return {
        "available": True,
        "score": -float(total / max(len(rp), len(qp))),
        "matched_event_indices": pairs,
        "omitted_reference_positions": omitted,
        "inserted_query_positions": inserted,
        "matched_events": len(pairs),
        "reference_events": len(rp), "query_events": len(qp),
        "query_coverage": len(pairs) / len(qp),
        "reference_coverage": len(pairs) / len(rp),
        "global_pitch_shift_semitones": shift,
        "timing_scale": scale, "timing_offset_s": offset,
        "tempo_ratio": 1. / scale,
        "pitch_residual_semitones": pitch_residual.tolist(),
        "timing_residual_s": time_residual.tolist(),
        "pitch_loss": pitch_loss, "timing_loss": timing_loss,
        "gap_loss": float(gap_loss), "total_loss": float(total),
    }


def score_event_details(reference_description, query_description):
    """Return score and evidence; does not assign a winning memory or threshold.

    Candidate shifts generate DP proposals. One fixed affine-time refinement is
    evaluated for each proposal; the minimum measured loss is retained. This is
    a bounded proposal search, not a claim of globally optimizing all possible
    joint alignment, pitch-shift, and time-transform combinations.
    """
    rp, rt, rvalid = _read(reference_description)
    qp, qt, qvalid = _read(query_description)
    if not rvalid or not qvalid:
        return {"available": False, "score": float(PARAMETERS["unavailable_score"]),
                "reason": "Need at least two finite events with strictly increasing measured onsets in each trace.",
                "matched_event_indices": [], "omitted_reference_positions": [], "inserted_query_positions": []}
    shifts = np.unique(np.r_[0., np.round((qp[None, :] - rp[:, None]).ravel(),
                                         PARAMETERS["shift_hypothesis_round_decimals"])])
    normalized_rt = (rt - rt[0]) / (rt[-1] - rt[0])
    normalized_qt = (qt - qt[0]) / (qt[-1] - qt[0])
    proposal_time_cost = PARAMETERS["proposal_normalized_time_weight"] * np.abs(normalized_rt[:, None] - normalized_qt[None, :])
    best = None
    evaluated_paths = set()

    def consider(alignment):
        nonlocal best
        key = tuple(alignment[0])
        measured = _fit_and_measure(rp, rt, qp, qt, alignment)
        if measured is None:
            return None
        if key not in evaluated_paths:
            evaluated_paths.add(key)
            better = best is None or measured["score"] > best["score"] + PARAMETERS["numerical_tie_tolerance"]
            equal = best is not None and abs(measured["score"] - best["score"]) <= PARAMETERS["numerical_tie_tolerance"]
            if better or (equal and measured["matched_events"] > best["matched_events"]):
                best = measured
        return measured

    for shift in shifts:
        pitch_cost = _deadzone(qp[None, :] - rp[:, None] - shift,
                               PARAMETERS["pitch_deadzone_semitones"]) / PARAMETERS["pitch_scale_semitones"]
        measured = consider(_align(pitch_cost + proposal_time_cost))
        for _ in range(PARAMETERS["refinement_passes"]):
            if measured is None:
                break
            pitch_cost = _deadzone(qp[None, :] - rp[:, None] - measured["global_pitch_shift_semitones"],
                                   PARAMETERS["pitch_deadzone_semitones"]) / PARAMETERS["pitch_scale_semitones"]
            timing_cost = PARAMETERS["timing_weight"] * _deadzone(qt[None, :] - (measured["timing_scale"] * rt[:, None] + measured["timing_offset_s"]),
                                                                                PARAMETERS["timing_deadzone_s"]) / PARAMETERS["timing_scale_s"]
            measured = consider(_align(pitch_cost + timing_cost))
    if best is None:
        return {"available": False, "score": float(PARAMETERS["unavailable_score"]),
                "reason": "No proposal retained at least two matched events.",
                "matched_event_indices": [], "omitted_reference_positions": [], "inserted_query_positions": []}
    best["proposal_paths_evaluated"] = len(evaluated_paths)
    return best


def score_events(reference_description, query_description) -> float:
    """Return only the score (higher is better); all gaps retain a positive cost."""
    return float(score_event_details(reference_description, query_description)["score"])
