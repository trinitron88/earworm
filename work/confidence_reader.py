"""Candidate-specific evidence from the unchanged Experiment06 alignment.

This is a stateless engineering compatibility rule, not a probability or a
perceptual identity model. The chosen Experiment06 path is reused exactly. The
reader never lowers a gap penalty, searches for a different path, reranks memory
items, or consumes the true source, split, edit family, or note metadata.

Residual evidence is conditional on *observed* coverage: all query events must
match, at least five sixths of reference events must survive, and no query event
may be inserted. This prevents a cheap two-of-six match from passing. A single
residual threshold can then be calibrated on development examples without
routing by a supplied edit label. Every compatible memory should be retained by
the caller, including mutually ambiguous candidates.

Affine timing offset and scale remain diagnostics. They do not enter a new
anchor gate: block alignment and a generator's lead-in are not identity facts.
"""
from __future__ import annotations

import math

import numpy as np

from incomplete_matcher import score_event_details


GUARDS = {
    "min_reference_coverage": 5. / 6.,
    "min_query_coverage": 1.,
    "max_inserted_events": 0,
    "min_matched_events": 2,
}
NUMERICAL_TOLERANCE = 1e-12
UNAVAILABLE_RESIDUAL = 1e6


def _count(description):
    values = np.asarray(description["event_pitch_semitones"])
    return len(values) if values.ndim == 1 else 0


def candidate_evidence(reference_description, query_description) -> dict:
    """Return numeric evidence for one candidate, using its original chosen path.

    Unavailable evidence has available=0 and a finite large residual sentinel.
    Timing/pitch diagnostics are zero-filled in that case and must not be read as
    measurements. No result is cached, and neither input is modified.
    """
    details = score_event_details(reference_description, query_description)
    reference_count, query_count = _count(reference_description), _count(query_description)
    if not details["available"]:
        return {
            "available": 0, "reference_events": reference_count,
            "query_events": query_count, "matched_events": 0,
            "omitted_events": reference_count, "inserted_events": query_count,
            "reference_coverage": 0., "query_coverage": 0.,
            "pitch_loss_per_match": UNAVAILABLE_RESIDUAL,
            "timing_loss_per_match": UNAVAILABLE_RESIDUAL,
            "residual_per_match": UNAVAILABLE_RESIDUAL,
            "score06": float(details["score"]),
            "original06_score": float(details["score"]), "original06_gap_loss": 0.,
            "global_pitch_shift_semitones": 0., "timing_scale": 0.,
            "timing_offset_s": 0., "tempo_ratio": 0.,
            "max_abs_pitch_residual_semitones": UNAVAILABLE_RESIDUAL,
            "max_abs_timing_residual_s": UNAVAILABLE_RESIDUAL,
        }
    matched = int(details["matched_events"])
    pitch = float(details["pitch_loss"]) / matched
    timing = float(details["timing_loss"]) / matched
    return {
        "available": 1, "reference_events": int(details["reference_events"]),
        "query_events": int(details["query_events"]), "matched_events": matched,
        "omitted_events": len(details["omitted_reference_positions"]),
        "inserted_events": len(details["inserted_query_positions"]),
        "reference_coverage": float(details["reference_coverage"]),
        "query_coverage": float(details["query_coverage"]),
        "pitch_loss_per_match": pitch, "timing_loss_per_match": timing,
        "residual_per_match": pitch + timing,
        "score06": float(details["score"]),
        "original06_score": float(details["score"]),
        "original06_gap_loss": float(details["gap_loss"]),
        "global_pitch_shift_semitones": float(details["global_pitch_shift_semitones"]),
        "timing_scale": float(details["timing_scale"]),
        "timing_offset_s": float(details["timing_offset_s"]),
        "tempo_ratio": float(details["tempo_ratio"]),
        "max_abs_pitch_residual_semitones": float(np.max(np.abs(details["pitch_residual_semitones"]))),
        "max_abs_timing_residual_s": float(np.max(np.abs(details["timing_residual_s"]))),
    }


def compatible(evidence: dict, config: dict) -> bool:
    """Gate one candidate; callers must keep all candidates that pass.

    config['max_residual_per_match'] is the sole adjustable decision parameter.
    The optional guard fields, when recorded in config, must match GUARDS; this
    prevents an accidental relaxation of coverage during threshold calibration.
    Other configuration provenance fields are ignored. The residual scale keeps
    Experiment06's pitch normalization, timing weight, and physical dead zones.
    """
    threshold = float(config["max_residual_per_match"])
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("max_residual_per_match must be finite and nonnegative.")
    for key, fixed in GUARDS.items():
        if key in config and (not math.isfinite(float(config[key]))
                              or abs(float(config[key]) - fixed) > NUMERICAL_TOLERANCE):
            raise ValueError(f"{key} is fixed at {fixed}; it is not a calibration parameter.")
    if evidence.get("available") != 1:
        return False
    fields = ("reference_events", "query_events", "matched_events", "omitted_events", "inserted_events",
              "reference_coverage", "query_coverage", "pitch_loss_per_match", "timing_loss_per_match", "residual_per_match")
    if any(key not in evidence or not math.isfinite(float(evidence[key])) for key in fields):
        return False
    counts = [float(evidence[key]) for key in fields[:5]]
    if any(value < 0 or not value.is_integer() for value in counts):
        return False
    reference, query, matched, omitted, inserted = map(int, counts)
    if not reference or not query or matched > min(reference, query):
        return False
    if omitted != reference - matched or inserted != query - matched:
        return False
    if (abs(evidence["reference_coverage"] - matched / reference) > NUMERICAL_TOLERANCE
            or abs(evidence["query_coverage"] - matched / query) > NUMERICAL_TOLERANCE):
        return False
    if any(evidence[key] < -NUMERICAL_TOLERANCE for key in fields[7:]):
        return False
    if abs(evidence["residual_per_match"] - evidence["pitch_loss_per_match"] - evidence["timing_loss_per_match"]) > NUMERICAL_TOLERANCE:
        return False
    return bool(
        matched >= GUARDS["min_matched_events"]
        and matched / reference + NUMERICAL_TOLERANCE >= GUARDS["min_reference_coverage"]
        and matched / query + NUMERICAL_TOLERANCE >= GUARDS["min_query_coverage"]
        and inserted <= GUARDS["max_inserted_events"]
        and evidence["residual_per_match"] <= threshold
    )
