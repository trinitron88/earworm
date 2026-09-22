"""Frozen family-weighted analysis for borrowed-recurrence-feasibility-v1.

This module consumes committed predictions and independently supplied labels. It
never loads PCM, score files, model weights, or evaluation-generation metadata.
Similarity distances are not probabilities. Localization remains diagnostic;
identity uses only the preregistered center-to-occurrence mapping.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 2026092201
RESAMPLES = 5000
CELLS = ("unchanged", "transpose", "stretch", "foil")
POSITIVE_CELLS = CELLS[:3]
CONDITIONS = ("full", "recent", "removed")
STRATA = ("bach", "novel")
AUDIO_ROUTES = ("standard", "mert6", "mert12")
ALL_ROUTES = AUDIO_ROUTES + ("ceiling",)
INTEGRITY_CHECKS = ("software", "provenance", "access", "eviction", "evidence")


def finite(value):
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool) and math.isfinite(float(value))


def numeric(value):
    return float(value) if finite(value) else None


def mean(values):
    vals = [float(v) for v in values if finite(v)]
    return sum(vals) / len(vals) if vals else None


def canonical_prediction(record):
    p = record.get("prediction") or {}
    h = p.get("hypothesis") or {}
    return {
        "available": bool(p.get("available", h or finite(p.get("distance")))),
        "distance": numeric(p.get("distance")),
        "onset": numeric(p.get("onset", h.get("start"))),
        "offset": numeric(p.get("offset", h.get("end"))),
        "shift": numeric(p.get("shift", h.get("shift"))),
        "stretch": numeric(p.get("stretch", h.get("stretch"))),
        "compute_seconds": numeric(p.get("compute_seconds")),
        "query_support": p.get("query_support"),
    }


def occurrences(labels):
    out = []
    for i, occ in enumerate(labels.get("equivalent_occurrences") or []):
        a = numeric(occ.get("onset", occ.get("start")))
        b = numeric(occ.get("offset", occ.get("end")))
        if a is not None and b is not None and b > a:
            out.append({"id": occ.get("id", str(i)), "onset": a, "offset": b})
    if not out:
        a, b = numeric(labels.get("source_onset")), numeric(labels.get("source_offset"))
        if a is not None and b is not None and b > a:
            out.append({"id": labels.get("source_id", "source"), "onset": a, "offset": b})
    return out


def score(record, threshold):
    """Score a committed response; no localization tolerance is an identity gate."""
    p = canonical_prediction(record)
    positive = record["cell"] != "foil"
    accepted = bool(p["available"] and p["distance"] is not None and threshold is not None and p["distance"] <= threshold)
    bounds = p["onset"] is not None and p["offset"] is not None and p["offset"] > p["onset"]
    center = (p["onset"] + p["offset"]) / 2 if bounds else None
    equiv = occurrences(record["labels"])
    matches = [o for o in equiv if center is not None and o["onset"] <= center < o["offset"]]
    identity = bool(accepted and matches) if positive else not accepted
    loc = None
    if positive and bounds and equiv:
        # Nearest equivalent interval for diagnostics, even if the identity fails.
        loc = min(equiv, key=lambda o: abs(center - (o["onset"] + o["offset"]) / 2))
    truth_shift = numeric(record["labels"].get("shift"))
    truth_stretch = numeric(record["labels"].get("stretch"))
    shift_error = abs(p["shift"] - truth_shift) if positive and p["shift"] is not None and truth_shift is not None else None
    stretch_error = abs(p["stretch"] / truth_stretch - 1) if positive and p["stretch"] is not None and truth_stretch is not None and truth_stretch > 0 else None
    shift_correct = shift_error is not None and shift_error <= 1.0 + 1e-12
    stretch_correct = stretch_error is not None and stretch_error <= .1 + 1e-12
    transformation_correct = shift_correct and stretch_correct
    overlap = max(0., min(p["offset"], loc["offset"]) - max(p["onset"], loc["onset"])) if loc else None
    union = max(p["offset"], loc["offset"]) - min(p["onset"], loc["onset"]) if loc else None
    unchanged_known = record["cell"] == "unchanged" and p["shift"] is not None and p["stretch"] is not None
    false_transform = unchanged_known and (abs(p["shift"]) > 1 + 1e-12 or abs(p["stretch"] - 1) > .1 + 1e-12)
    q = p["query_support"]
    query_bounds = isinstance(q, (list, tuple)) and len(q) == 2 and finite(q[0]) and finite(q[1]) and q[1] > q[0]
    labels = record["labels"]
    out = {
        "group": str(record["group"]), "stratum": record["stratum"], "cell": record["cell"],
        "route": record["route"], "condition": record["condition"],
        "accepted": int(accepted), "abstention": int(not accepted), "available": int(p["available"]),
        "correct_identity": int(identity), "false_accept": int(accepted) if not positive else None,
        "shift_correct": int(shift_correct) if positive else None,
        "stretch_correct": int(stretch_correct) if positive else None,
        "transformation_correct": int(transformation_correct) if positive else None,
        "joint_correct": int(identity and transformation_correct) if positive else None,
        "unchanged_false_transform": int(accepted and false_transform) if record["cell"] == "unchanged" else None,
        "unchanged_false_transform_among_accepted": int(false_transform) if record["cell"] == "unchanged" and accepted else None,
        "unchanged_transform_unavailable": int(not unchanged_known) if record["cell"] == "unchanged" else None,
        "distance": p["distance"], "shift_abs_error_semitones": shift_error,
        "stretch_abs_relative_error": stretch_error,
        "onset_signed_error_seconds": p["onset"] - loc["onset"] if loc else None,
        "offset_signed_error_seconds": p["offset"] - loc["offset"] if loc else None,
        "onset_abs_error_seconds": abs(p["onset"] - loc["onset"]) if loc else None,
        "offset_abs_error_seconds": abs(p["offset"] - loc["offset"]) if loc else None,
        "overlap_seconds": overlap, "intersection_over_union": overlap / union if loc and union > 0 else None,
        "equivalent_source_coverage": overlap / (loc["offset"] - loc["onset"]) if loc else None,
        "accepted_correct_localization_iou": overlap / union if loc and accepted and identity and union > 0 else None,
        "matched_occurrence_id": matches[0]["id"] if positive and accepted and matches else None,
        "query_onset_signed_error_seconds": q[0] - labels["query_onset"] if query_bounds and finite(labels.get("query_onset")) else None,
        "query_offset_signed_error_seconds": q[1] - labels["query_offset"] if query_bounds and finite(labels.get("query_offset")) else None,
        "decision_compute_seconds": p["compute_seconds"],
    }
    return out


def select(devrecords):
    """Select one threshold per route and one of two fixed MERT candidates.

    Full-state development data only. Grid = 0,.01,...,1. A route with no
    feasible grid member receives null (abstain all) and cannot qualify.
    Ties: smaller threshold; MERT ties: identity, joint, then layer 6.
    """
    thresholds, diagnostics = {}, {}
    for route in ALL_ROUTES:
        rows = [r for r in devrecords if r.get("route") == route and r.get("condition") == "full"]
        pos = [r for r in rows if r.get("cell") in POSITIVE_CELLS]
        foil = [r for r in rows if r.get("cell") == "foil"]
        candidates = []
        for i in range(101):
            threshold = i / 100
            s = [score(r, threshold) for r in rows]
            pp = [r for r in s if r["cell"] in POSITIVE_CELLS]
            ff = [r for r in s if r["cell"] == "foil"]
            identity = _family_mean(pp, "correct_identity")
            far = _family_mean(ff, "false_accept")
            joint = _family_mean(pp, "joint_correct")
            if pos and foil and far is not None and far <= .1 + 1e-12:
                candidates.append((identity, -threshold, joint, threshold, far))
        if candidates:
            # The threshold tie does not use joint performance.
            winner = max(candidates, key=lambda x: (x[0], x[1]))
            thresholds[route] = winner[3]
            diagnostics[route] = {"selection_feasible": True, "positive_identity": winner[0], "positive_joint": winner[2], "foil_false_accept": winner[4], "full_records": len(rows), "feasible_grid_members": len(candidates)}
        else:
            thresholds[route] = None
            diagnostics[route] = {"selection_feasible": False, "positive_identity": 0., "positive_joint": 0., "foil_false_accept": None, "full_records": len(rows), "feasible_grid_members": 0}
    chosen = max(("mert6", "mert12"), key=lambda r: (diagnostics[r]["selection_feasible"], diagnostics[r]["positive_identity"], diagnostics[r]["positive_joint"], r == "mert6"))
    return {"thresholds": thresholds, "selected_mert": chosen, "diagnostics": diagnostics,
            "grid": {"start": 0, "stop": 1, "step": .01},
            "selection_rule": "Maximize full-state equal-family positive identity subject to full-state overall foil FAR <= .1; threshold ties favor the smaller threshold. MERT: identity then joint then layer6. Null means no feasible grid member, explicit abstain-all."}


def _family_mean(rows, key):
    groups = defaultdict(list)
    for r in rows:
        if finite(r.get(key)):
            groups[r["group"]].append(float(r[key]))
    return mean([mean(v) for v in groups.values()])


class FamilyBootstrap:
    def __init__(self, group_strata):
        rng = np.random.default_rng(SEED)
        self.groups, self.indices = {}, {}
        for stratum in ("all",) + STRATA:
            names = sorted(g for g, s in group_strata.items() if stratum == "all" or s == stratum)
            self.groups[stratum] = names
            self.indices[stratum] = rng.integers(0, len(names), size=(RESAMPLES, len(names))) if names else None

    def metric(self, rows, key, stratum="all"):
        grouped = defaultdict(list)
        for r in rows:
            if finite(r.get(key)):
                grouped[r["group"]].append(float(r[key]))
        names = self.groups[stratum]
        vals = np.array([mean(grouped[g]) if grouped[g] else np.nan for g in names], dtype=float)
        valid = np.isfinite(vals)
        if not np.any(valid):
            return {"value": None, "ci95": [None, None], "n_groups": 0, "n_observations": 0}
        sampled = vals[self.indices[stratum]]
        count = np.isfinite(sampled).sum(axis=1)
        means = np.divide(np.nansum(sampled, axis=1), count, out=np.full(RESAMPLES, np.nan), where=count > 0)
        means = means[np.isfinite(means)]
        interval = np.quantile(means, [.025, .975]).tolist() if len(means) else [None, None]
        return {"value": float(np.mean(vals[valid])), "ci95": [float(v) for v in interval], "n_groups": int(valid.sum()), "n_observations": sum(len(v) for v in grouped.values())}


METRICS = (
    "correct_identity", "false_accept", "accepted", "abstention", "available",
    "shift_correct", "stretch_correct", "transformation_correct", "joint_correct",
    "unchanged_false_transform", "unchanged_false_transform_among_accepted", "unchanged_transform_unavailable",
    "distance", "shift_abs_error_semitones", "stretch_abs_relative_error",
    "onset_signed_error_seconds", "offset_signed_error_seconds", "onset_abs_error_seconds", "offset_abs_error_seconds",
    "overlap_seconds", "intersection_over_union", "equivalent_source_coverage", "accepted_correct_localization_iou",
    "query_onset_signed_error_seconds", "query_offset_signed_error_seconds", "decision_compute_seconds",
)


def summaries(rows, bootstrap):
    output = {}
    for stratum in ("all",) + STRATA:
        subset = [r for r in rows if stratum == "all" or r["stratum"] == stratum]
        output[stratum] = {"n_records": len(subset), "n_groups": len({r["group"] for r in subset}),
                           "accepted_count": sum(r["accepted"] for r in subset),
                           "abstention_count": sum(r["abstention"] for r in subset),
                           "correct_identity_count": sum(r["correct_identity"] for r in subset),
                           "metrics": {m: bootstrap.metric(subset, m, stratum) for m in METRICS}}
    return output


def history(rows, bootstrap):
    indexed = {(r["group"], r["cell"], r["condition"]): r for r in rows if r["cell"] in POSITIVE_CELLS}
    groups = sorted({r["group"] for r in rows})
    differences = []
    for control in ("recent", "removed"):
        for group in groups:
            for cell in POSITIVE_CELLS:
                a, b = indexed.get((group, cell, "full")), indexed.get((group, cell, control))
                if a is None or b is None:
                    continue
                differences.append({"group": group, "stratum": a["stratum"], "control": control,
                                    "identity_difference": a["correct_identity"] - b["correct_identity"],
                                    "joint_difference": a["joint_correct"] - b["joint_correct"]})
    result = {}
    for control in ("recent", "removed"):
        result[control] = {}
        for stratum in ("all",) + STRATA:
            subset = [r for r in differences if r["control"] == control and (stratum == "all" or r["stratum"] == stratum)]
            result[control][stratum] = {"identity": bootstrap.metric(subset, "identity_difference", stratum),
                                         "joint": bootstrap.metric(subset, "joint_difference", stratum)}
    return result


def status_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and isinstance(value.get("passed"), bool):
        return value["passed"]
    return None


def route_check(checks, route, key):
    value = (checks.get("routes", {}).get(route, {}) or {}).get(key, checks.get(key))
    return status_bool(value)


def _threshold_gate(metric, threshold, direction="min"):
    value = metric["value"]
    lo, hi = metric["ci95"]
    return {"passed": None if value is None else (value >= threshold - 1e-12 if direction == "min" else value <= threshold + 1e-12),
            "value": value, "criterion": (">=" if direction == "min" else "<=") + str(threshold),
            "ci95": [lo, hi], "interval_crosses_point_threshold": bool(lo is not None and hi is not None and lo < threshold < hi)}


def analyze(records, thresholds, checks, resource):
    """Return a JSON-safe complete report, with A/B/C/INVALID precedence.

    checks required keys: software/provenance/access/eviction/evidence;
    preservation for audio routes. Each may be bool or {passed: bool,...}.
    Optional overrides: checks.routes[route]. Missing proof is C/inconclusive,
    not a fabricated pass. expected_groups defaults to the observed group count.
    Resource: executions, aggregate_compute_seconds, new_artifact_bytes,
    external_spend_usd, and routes[route] with max_decision_latency_seconds,
    extraction_matching_rtf, peak_persistent_bytes, raw_ring_seconds,
    raw_ring_chunks; optional extraction_unit_seconds, acquisition_bytes.
    """
    started = time.perf_counter()
    selection = thresholds if "thresholds" in thresholds else {"thresholds": thresholds, "selected_mert": checks.get("selected_mert")}
    selected = selection.get("selected_mert")
    errors, missing, invalid_reasons = [], [], []
    if selected not in ("mert6", "mert12"):
        errors.append("selected_mert must name exactly one declared MERT candidate")
    selected_routes = ("standard", selected, "ceiling") if selected in ("mert6", "mert12") else ("standard", "ceiling")
    threshold_map = selection["thresholds"]
    considered, group_strata, seen = [], {}, set()
    for number, record in enumerate(records):
        route = record.get("route")
        if route not in ALL_ROUTES:
            errors.append(f"record {number}: unknown route {route!r}")
            continue
        if route not in selected_routes:
            continue
        if record.get("cell") not in CELLS or record.get("condition") not in CONDITIONS or record.get("stratum") not in STRATA:
            errors.append(f"record {number}: unknown cell, condition, or stratum")
            continue
        if "group" not in record or not isinstance(record.get("labels"), dict) or not isinstance(record.get("prediction"), dict):
            errors.append(f"record {number}: missing group/labels/prediction")
            continue
        group = str(record["group"])
        key = group, record["cell"], route, record["condition"]
        if key in seen:
            errors.append(f"duplicate record: {key!r}")
        seen.add(key)
        if group in group_strata and group_strata[group] != record["stratum"]:
            errors.append(f"family {group}: inconsistent material stratum")
        group_strata[group] = record["stratum"]
        if record["cell"] in POSITIVE_CELLS and not occurrences(record["labels"]):
            errors.append(f"record {number}: no independent equivalent occurrence interval")
        for label in ("shift", "stretch"):
            if record["cell"] in POSITIVE_CELLS and not finite(record["labels"].get(label)):
                errors.append(f"record {number}: missing numeric positive transformation label {label}")
        if route not in threshold_map:
            missing.append(f"missing frozen threshold for {route}")
        elif threshold_map[route] is not None and (not finite(threshold_map[route]) or not 0 <= threshold_map[route] <= 1):
            errors.append(f"invalid frozen threshold for {route}")
        considered.append(record)
    expected_groups = checks.get("expected_groups", len(group_strata))
    if not group_strata:
        missing.append("no evaluable family records")
    if len(group_strata) != expected_groups:
        errors.append(f"expected {expected_groups} groups; found {len(group_strata)}")
    if checks.get("expected_groups") is not None:
        for stratum in STRATA:
            actual = sum(s == stratum for s in group_strata.values())
            if actual * 2 != expected_groups:
                errors.append(f"{stratum}: expected half of {expected_groups} groups; found {actual}")
    for group in group_strata:
        for route in selected_routes:
            for condition in CONDITIONS:
                for cell in CELLS:
                    if (group, cell, route, condition) not in seen:
                        errors.append(f"missing comparison row: {(group,cell,route,condition)!r}")
    if errors:
        invalid_reasons.extend("schema: " + error for error in errors)
    scored = [score(r, threshold_map.get(r["route"])) for r in considered]
    bootstrap = FamilyBootstrap(group_strata)
    control_failures = [dict(group=r["group"], route=r["route"], condition=r["condition"], cell=r["cell"])
                        for r in scored if r["cell"] in POSITIVE_CELLS and r["condition"] != "full" and r["correct_identity"]]
    if control_failures:
        invalid_reasons.append("source identity recovered after source evidence was removed: control failure or metric flaw")
    hard_limits = {
        "executions": (1000, resource.get("executions")),
        "aggregate_compute_seconds": (7200, resource.get("aggregate_compute_seconds")),
        "new_artifact_bytes": (2 * 1024 ** 3, resource.get("new_artifact_bytes")),
        "external_spend_usd": (0, resource.get("external_spend_usd")),
    }
    if "acquisition_bytes" in resource:
        hard_limits["acquisition_bytes"] = (25 * 1024 ** 2, resource["acquisition_bytes"])
    hard_resource = {}
    for key, (limit, value) in hard_limits.items():
        passed = finite(value) and 0 <= value <= limit
        hard_resource[key] = {"value": numeric(value), "maximum": limit, "passed": passed if finite(value) else None}
        if not finite(value):
            missing.append("missing resource measurement: " + key)
        elif not passed:
            invalid_reasons.append("assignment hard resource ceiling: " + key)
    reports, all_route_gates = {}, {}
    for route in selected_routes:
        rows = [r for r in scored if r["route"] == route]
        report = {"threshold": threshold_map.get(route), "selected_audio_candidate": route == selected,
                  "hybrid": route.startswith("mert"),
                  "sidecar_access": "MERT correspondence uses MERT features; transformation shift uses sidecar chroma" if route.startswith("mert") else ("acoustic features and preserved spectral/energy/time evidence" if route == "standard" else "clean score/construction observations only; no acoustic sidecar gate"),
                  "conditions": {}, "history_benefit": history(rows, bootstrap)}
        for condition in CONDITIONS:
            cr = [r for r in rows if r["condition"] == condition]
            report["conditions"][condition] = {cell: summaries([r for r in cr if r["cell"] == cell], bootstrap) for cell in CELLS}
            report["conditions"][condition]["positive_pooled"] = summaries([r for r in cr if r["cell"] in POSITIVE_CELLS], bootstrap)
        gates = {}
        for cell in POSITIVE_CELLS:
            for stratum in ("all",) + STRATA:
                metric = report["conditions"]["full"][cell][stratum]["metrics"]["correct_identity"]
                gates[f"identity/{cell}/{stratum}"] = _threshold_gate(metric, .8)
        for cell in ("transpose", "stretch"):
            metric = report["conditions"]["full"][cell]["all"]["metrics"]["joint_correct"]
            gates[f"joint/{cell}"] = _threshold_gate(metric, .8)
        metric = report["conditions"]["full"]["foil"]["all"]["metrics"]["false_accept"]
        gates["foil_false_accept"] = _threshold_gate(metric, .1, "max")
        for control in ("recent", "removed"):
            result = report["history_benefit"][control]["all"]["identity"]
            lo = result["ci95"][0]
            gates["history/" + control] = {"value": result["value"], "ci95": result["ci95"], "criterion": "lower95 > 0", "passed": None if lo is None else lo > 0}
        for key in INTEGRITY_CHECKS + (() if route == "ceiling" else ("preservation",)):
            passed = route_check(checks, route, key)
            gates["check/" + key] = {"passed": passed}
            if passed is None:
                missing.append(f"{route}: missing check {key}")
            elif not passed and key in INTEGRITY_CHECKS:
                invalid_reasons.append(f"{route}: failed {key} check")
        rr = resource.get("routes", {}).get(route, {}) or {}
        for key, limit in (("peak_persistent_bytes", 8 * 1024 ** 2), ("raw_ring_seconds", 4), ("raw_ring_chunks", 32)):
            value = rr.get(key)
            passed = None if not finite(value) else 0 <= value <= limit
            gates["resource/" + key] = {"value": numeric(value), "maximum": limit, "passed": passed}
            if passed is None:
                missing.append(f"{route}: missing resource measurement {key}")
            elif not passed:
                invalid_reasons.append(f"{route}: state/ring limit failure {key}")
        if "extraction_unit_seconds" in rr:
            value = rr["extraction_unit_seconds"]
            passed = finite(value) and 0 <= value <= 2
            gates["resource/extraction_unit_seconds"] = {"value": numeric(value), "maximum": 2, "passed": passed}
            if not passed:
                invalid_reasons.append(f"{route}: extraction context unit limit failure")
        for key, limit in (("max_decision_latency_seconds", 5), ("extraction_matching_rtf", 1)):
            value = rr.get(key)
            passed = None if not finite(value) else 0 <= value <= limit
            gates["performance/" + key] = {"value": numeric(value), "maximum": limit, "passed": passed}
            if passed is None:
                missing.append(f"{route}: missing performance measurement {key}")
        gates["threshold_selection"] = {"passed": threshold_map.get(route) is not None}
        statuses = [g["passed"] for g in gates.values()]
        report["gates"] = gates
        report["qualifies"] = all(s is True for s in statuses)
        report["gate_status"] = "pass" if report["qualifies"] else ("fail" if False in statuses else "inconclusive")
        report["failed_gates"] = [k for k, v in gates.items() if v["passed"] is False]
        report["unresolved_gates"] = [k for k, v in gates.items() if v["passed"] is None]
        report["resource"] = rr
        # Calibration by distance bins, with both material strata and all conditions.
        report["score_reliability"] = []
        report["score_reliability_unbinned_records"] = sum(r["distance"] is None or not 0 <= r["distance"] <= 1 for r in rows)
        for condition in CONDITIONS:
            for lower in (0., .2, .4, .6, .8):
                subset = [r for r in rows if r["condition"] == condition and r["distance"] is not None and lower <= r["distance"] and (r["distance"] < lower + .2 or lower == .8 and r["distance"] <= 1)]
                report["score_reliability"].append({"condition": condition, "distance_bin": [lower, round(lower + .2, 10)], "n_records": len(subset), "mean_distance": _family_mean(subset, "distance"), "correct_decision": _family_mean(subset, "correct_identity"), "accepted": _family_mean(subset, "accepted")})
        reports[route] = report
        all_route_gates[route] = report["qualifies"]
    invalid_reasons = sorted(set(invalid_reasons))
    missing = sorted(set(missing))
    adequate = [r for r in ("standard", selected) if r in reports and reports[r]["qualifies"]]
    if len(adequate) > 1:
        for route in adequate:
            if not finite(resource.get("routes", {}).get(route, {}).get("end_to_end_compute_seconds")):
                missing.append(f"{route}: missing measured end-to-end compute for simplest adequate route selection")
    missing = sorted(set(missing))
    chosen, reason = None, None
    if invalid_reasons:
        decision, reason = "INVALID", "Integrity, control, schema, or assignment hard-resource failure; no scientific negative or automatic restart."
    elif missing:
        decision, reason = "C", "Required evidence is incomplete; the comparison is inconclusive and does not establish acoustic-memory failure."
    elif adequate:
        def simplicity(route):
            rr = resource.get("routes", {}).get(route, {})
            compute = rr.get("end_to_end_compute_seconds")
            retained = rr.get("peak_persistent_bytes")
            return (float(compute) if finite(compute) else math.inf, float(retained) if finite(retained) else math.inf, route != "standard")
        chosen = min(adequate, key=simplicity)
        decision, reason = "A", "At least one audio route meets the frozen gates; choose the lowest measured compute, then retained bytes, among adequate routes."
    elif reports.get("ceiling", {}).get("qualifies"):
        decision, reason = "B", "Neither audio route qualifies but the clean-observation ceiling passes; leave memory architecture undecided and localize the observation/representation limitation."
    else:
        decision, reason = "C", "The clean ceiling does not pass the corresponding comparison; reconsider correspondence/test design before adding a memory controller."
    result = {
        "schema_version": 1, "assignment": "earworm-borrowed-recurrence-feasibility-v1",
        "decision": decision, "reason": reason, "selected_route": chosen, "selected_mert": selected,
        "adequate_audio_routes": adequate, "routes": reports, "selection": selection,
        "bootstrap": {"resamples": RESAMPLES, "seed": SEED, "unit": "piece/motif family", "weighting": "equal family; positive history averages the three cells within family", "pairing": "shared family draws across routes, cells, conditions; stratum intervals resample families within stratum", "interval": "percentile 2.5% and 97.5%"},
        "identity_mapping": "Accepted hypothesis center lies within an independently preregistered equivalent earlier occurrence, with onset inclusive and offset exclusive. No overlap or boundary-accuracy gate.",
        "transformation_rule": "Shift absolute error <=1 semitone AND stretch absolute relative error <=10%; joint also requires accepted correct identity.",
        "false_transform_rule": "Unchanged accepted response exceeds either shift ±1 semitone or stretch ±10%; unavailable estimates are reported separately.",
        "confidence_warning": "Distances are uncalibrated scores, not probabilities. Thresholds are selected on development only; null means no feasible grid member and abstain-all.",
        "scope": "Rendered isolated score voices and newly composed motifs; construction equivalences are not human perceptual identity.",
        "counts": {"input_records": len(records), "analyzed_records": len(considered), "ignored_unselected_candidate_records": len(records) - len(considered), "groups": len(group_strata), "groups_by_stratum": {s: sum(v == s for v in group_strata.values()) for s in STRATA}},
        "schema_errors": errors, "control_failures": control_failures, "invalid_reasons": invalid_reasons,
        "missing_evidence": missing, "hard_resource_gates": hard_resource, "checks": checks, "resource": resource,
        "scored_records": scored, "analysis_compute_seconds": time.perf_counter() - started,
    }
    # Reject accidental NaN/Infinity rather than silently emitting nonstandard JSON.
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--checks", type=Path)
    parser.add_argument("--resource", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--select", action="store_true")
    args = parser.parse_args()
    records = json.loads(args.records.read_text())
    if args.select:
        result = select(records)
    else:
        if not all((args.selection, args.checks, args.resource)):
            parser.error("analysis requires --selection, --checks and --resource")
        result = analyze(records, json.loads(args.selection.read_text()), json.loads(args.checks.read_text()), json.loads(args.resource.read_text()))
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
