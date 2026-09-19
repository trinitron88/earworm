"""Compare retained saved paths in acoustic coordinates; no new path search or scoring."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, separators=(",", ":")) if isinstance(v, (list, dict)) else v
                             for k, v in row.items()})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def event(description, index):
    return {"onset_s": float(description["event_onset_s"][index]),
            "offset_s": float(description["event_offset_s"][index]),
            "pitch_semitones": float(description["event_pitch_semitones"][index])}


def max_difference(left, right):
    if len(left) != len(right):
        return None
    return max((abs(a - b) for a, b in zip(left, right)), default=0.0)


def inspect_path(path, evidence, reference, query):
    """Describe a stored path, retaining common query-time coordinates and raw values."""
    pairs = path["matched_pairs"]
    ri, qi = np.array(pairs, dtype=int).T
    rp = reference["event_pitch_semitones"][ri].astype(float)
    qp = query["event_pitch_semitones"][qi].astype(float)
    rt = reference["event_onset_s"][ri].astype(float)
    qt = query["event_onset_s"][qi].astype(float)
    shift, scale, offset = (path[k] for k in ("global_pitch_shift", "timing_scale", "timing_offset_s"))
    assert scale > 0 and len(set(ri)) == len(ri) and len(set(qi)) == len(qi)
    pitch_residual = qp - rp - shift
    timing_residual = qt - scale * rt - offset
    checks = [(pitch_residual, path["pitch_residual_semitones"]),
              (timing_residual, path["timing_residual_s"]),
              (qp - rp, path["absolute_pitch_change_semitones"]),
              (qt - rt, path["onset_change_s"])]
    error = max(float(np.max(np.abs(a - b))) for a, b in checks)
    pitch_loss = np.maximum(np.abs(pitch_residual) - .05, 0) / 2
    timing_loss = np.maximum(np.abs(timing_residual) - .005, 0) * 2
    cost = float((pitch_loss.sum() + timing_loss.sum() + .7 * (len(path["missing_reference"]) + len(path["inserted_query"])))
                 / max(evidence["reference_events"], evidence["query_events"]))
    error = max(error, abs(cost - path["cost"]), abs(float(pitch_loss.mean()) - path["mean_pitch_loss"]),
                abs(float(timing_loss.mean()) - path["mean_timing_loss"]),
                abs(float(np.mean(np.abs(pitch_residual) <= .2)) - path["exact_pitch_fraction"]))
    assert error < 1e-12, "Saved arithmetic does not reconcile"
    # These sets reproduce membership already explicit in each saved record; no detector is executed.
    ref_eligible = sorted(set(map(int, ri)) | set(path["missing_reference"]))
    query_eligible = sorted(set(map(int, qi)) | set(path["inserted_query"]))
    assert len(ref_eligible) == evidence["reference_events"] and len(query_eligible) == evidence["query_events"]
    assert not set(ri) & set(path["missing_reference"]) and not set(qi) & set(path["inserted_query"])
    matched = []
    for order, (r, q) in enumerate(pairs):
        re, qe = event(reference, r), event(query, q)
        matched.append({"reference_event": r, "query_event": q, "reference": re, "query": qe,
                        "mapped_reference_onset_s": scale * re["onset_s"] + offset,
                        "mapped_reference_offset_s": scale * re["offset_s"] + offset,
                        "mapped_reference_pitch_semitones": re["pitch_semitones"] + shift,
                        "pitch_residual_semitones": path["pitch_residual_semitones"][order],
                        "timing_residual_s": path["timing_residual_s"][order],
                        "absolute_pitch_change_semitones": path["absolute_pitch_change_semitones"][order],
                        "onset_change_s": path["onset_change_s"][order]})
    missing = []
    for r in path["missing_reference"]:
        re = event(reference, r)
        before = [m["query"]["onset_s"] for m in matched if m["reference"]["onset_s"] < re["onset_s"]]
        after = [m["query"]["onset_s"] for m in matched if m["reference"]["onset_s"] > re["onset_s"]]
        missing.append({"reference_event": r, "reference": re,
                        "mapped_onset_s": scale * re["onset_s"] + offset,
                        "mapped_offset_s": scale * re["offset_s"] + offset,
                        "mapped_pitch_semitones": re["pitch_semitones"] + shift,
                        "pitch_from_first_matched_reference_semitones": re["pitch_semitones"] - float(rp[0]),
                        "preceding_matched_query_onset_s": before[-1] if before else None,
                        "following_matched_query_onset_s": after[0] if after else None})
    inserted = [{"query_event": q, **event(query, q)} for q in path["inserted_query"]]
    # The semantic signature omits opaque IDs and reference-local indices. Query events are
    # compared by their actual acoustic values in the same query, not by index identity.
    semantic = {
        "global_transform": [shift, scale, offset],
        "matched": [{k: v for k, v in m.items() if k not in ("reference_event", "query_event")} for m in matched],
        "missing": [{k: v for k, v in m.items() if k != "reference_event"} for m in missing],
        "inserted": [{k: v for k, v in m.items() if k != "query_event"} for m in inserted],
    }
    return {"semantic": semantic, "matched": matched, "missing": missing, "inserted": inserted,
            "reference_pitch_intervals": np.diff(rp).tolist(), "reference_onset_intervals_s": np.diff(rt).tolist(),
            "query_pitch_intervals": np.diff(qp).tolist(), "query_onset_intervals_s": np.diff(qt).tolist(),
            "pitch_residuals": list(path["pitch_residual_semitones"]), "timing_residuals_s": list(path["timing_residual_s"]),
            "reference_eligible": ref_eligible, "query_eligible": query_eligible, "arithmetic_error": error,
            "rebuilt_features": [cost, float(np.log1p(len(ri))), len(ri)/evidence["reference_events"],
                len(ri)/evidence["query_events"], float(pitch_loss.mean()), float(np.mean(np.abs(pitch_residual) <= .2)),
                float(timing_loss.mean()), len(path["missing_reference"])/evidence["reference_events"],
                len(path["inserted_query"])/evidence["query_events"],
                1-evidence["query_events"]/max(1, len(query["event_onset_s"])),
                float(np.log1p(evidence["reference_events"])), float(np.log1p(evidence["query_events"]))]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=HERE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Use a new or empty output directory")
    args.out.mkdir(parents=True, exist_ok=True)
    identifiers = json.loads((args.input / "input_identifiers.json").read_text())
    assert sha(args.input / "saved_inputs.json") == identifiers["selected_export"]["sha256"]
    inventory = json.loads((args.input / "inventory.json").read_text())
    if inventory["status"] != "complete":
        raise ValueError("Saved evidence incomplete; report inventory blocker instead of regenerating")
    data = json.loads((args.input / "saved_inputs.json").read_text())
    config = json.loads((ROOT / "work/accounts_results/frozen_config.json").read_text())
    for name, digest in identifiers["frozen_source_sha256"].items():
        assert sha(ROOT / "work" / name) == digest
    for rel in ("work/accounts_results/frozen_config.json", "work/accounts_results/protocol.json"):
        assert sha(ROOT / rel) == next(i["sha256"] for i in identifiers["original_inputs"] if i["path"] == rel)
    assert sha(ROOT / identifiers["selection_source"]["path"]) == identifiers["selection_source"]["sha256"]
    desc = {bid: {k: np.asarray(v["values"], dtype=v["dtype"]) for k, v in fields.items()}
            for bid, fields in data["descriptions"].items()}
    path_details, path_rows, match_rows, missing_rows, inserted_rows, event_rows = {}, [], [], [], [], []
    eligibility = {}
    max_error = max_feature_error = 0.0
    for bid, d in sorted(desc.items()):
        for i in range(len(d["event_onset_s"])):
            event_rows.append({"block_id": bid, "event_index": i, **event(d, i),
                "pitch_span_cents": float(d["event_pitch_span_cents"][i]),
                "phase_fraction": float(d["event_phase_fraction"][i]),
                "bend_peak_cents": float(d["event_bend_peak_cents"][i])})
    for qid, records in sorted(data["records"].items()):
        for rid, record in sorted(records.items()):
            assert record["status"] == "available"
            e = record["evidence"]
            assert e["available"]
            analyses = []
            for pi, path in enumerate(e["paths"]):
                detail = inspect_path(path, e, desc[rid], desc[qid])
                analyses.append(detail)
                max_error = max(max_error, detail["arithmetic_error"])
                if pi == 0:
                    error = max_difference(detail["rebuilt_features"], e["features"])
                    max_feature_error = max(max_feature_error, error)
                    assert error < 1e-12
                for bid, ids in ((rid, detail["reference_eligible"]), (qid, detail["query_eligible"])):
                    if bid in eligibility:
                        assert eligibility[bid] == ids, "Saved eligible event membership inconsistent"
                    eligibility[bid] = ids
                base = {"query_id": qid, "reference_id": rid, "path_index": pi, "used_for_support": pi == 0,
                        "role": "true_source" if rid == data["query_metadata"][qid]["true_reference"] else "maximum_candidate"}
                path_rows.append({**base, "matched_pairs": path["matched_pairs"], "missing_reference": path["missing_reference"],
                    "inserted_query": path["inserted_query"], "cost": path["cost"], "global_pitch_shift": path["global_pitch_shift"],
                    "timing_scale": path["timing_scale"], "timing_offset_s": path["timing_offset_s"],
                    "pitch_residuals": detail["pitch_residuals"], "timing_residuals_s": detail["timing_residuals_s"],
                    "matched_reference_pitch_intervals": detail["reference_pitch_intervals"],
                    "matched_reference_onset_intervals_s": detail["reference_onset_intervals_s"],
                    "matched_query_pitch_intervals": detail["query_pitch_intervals"],
                    "matched_query_onset_intervals_s": detail["query_onset_intervals_s"],
                    "mean_pitch_loss": path["mean_pitch_loss"], "mean_timing_loss": path["mean_timing_loss"],
                    "acoustic_signature_sha256": hashlib.sha256(canonical(detail["semantic"]).encode()).hexdigest()})
                for order, m in enumerate(detail["matched"]):
                    match_rows.append({**base, "correspondence_order": order, "reference_event": m["reference_event"],
                        "query_event": m["query_event"], **{"reference_"+k: v for k,v in m["reference"].items()},
                        **{"query_"+k: v for k,v in m["query"].items()},
                        **{k:v for k,v in m.items() if k not in ("reference_event", "query_event", "reference", "query")}})
                for order, m in enumerate(detail["missing"]):
                    missing_rows.append({**base, "missing_order": order, "reference_event": m["reference_event"],
                        **{"reference_"+k: v for k,v in m["reference"].items()},
                        **{k:v for k,v in m.items() if k not in ("reference_event", "reference")},
                        "interpretation": "expected location/pitch under saved alignment; not a query observation or proven cause"})
                for order, m in enumerate(detail["inserted"]):
                    inserted_rows.append({**base, "inserted_order": order, **m})
            path_details[qid, rid] = analyses
    # Add explicit saved eligibility membership to cached events, including rejected broad-span events.
    for row in event_rows:
        row["in_saved_eligible_set"] = row["event_index"] in eligibility[row["block_id"]]
    pair_rows = []
    for selection in data["selection"]:
        qid, true, candidate = (selection[k] for k in ("query_id", "true_reference", "candidate_id"))
        left, right = path_details[qid, true], path_details[qid, candidate]
        a, b = left[0], right[0]
        le = data["records"][qid][true]["evidence"]
        re = data["records"][qid][candidate]["evidence"]
        assert le["features"] == re["features"] and selection["source_score"] == selection["candidate_score"]
        frozen_score = float(np.dot((np.asarray(le["features"]) - config["mean"]) / config["scale"], config["coef"]) + config["intercept"])
        assert frozen_score == selection["source_score"]
        # Event-to-event comparison is anchored to the actual onsets in this common query.
        left_anchors = [m["query"]["onset_s"] for m in a["matched"]]
        right_anchors = [m["query"]["onset_s"] for m in b["matched"]]
        common_anchors = left_anchors == right_anchors
        left_signatures = sorted(canonical(p["semantic"]) for p in left)
        right_signatures = sorted(canonical(p["semantic"]) for p in right)
        missing_regions = lambda p: [[m["preceding_matched_query_onset_s"], m["following_matched_query_onset_s"]] for m in p["missing"]]
        deltas = {}
        for field in ("reference_pitch_intervals", "reference_onset_intervals_s", "pitch_residuals", "timing_residuals_s"):
            deltas["best_"+field+"_max_abs_difference"] = max_difference(a[field], b[field]) if common_anchors else None
        # Missing lists are ordered by reference time. Comparing their ordered hypotheses does
        # not assert that the two memories' missing events have a shared physical identity.
        for field in ("mapped_onset_s", "mapped_offset_s", "mapped_pitch_semitones", "pitch_from_first_matched_reference_semitones"):
            deltas["best_missing_"+field+"_max_abs_difference"] = max_difference([m[field] for m in a["missing"]], [m[field] for m in b["missing"]])
        row = {**selection, "group_id": data["query_metadata"][qid]["group_id"],
               "family": data["query_metadata"][qid]["family"], "status": "available",
               "true_path_count": len(left), "candidate_path_count": len(right),
               "both_have_no_retained_alternatives": len(left) == len(right) == 1,
               "retained_alternatives_only_multiset_equal": sorted(canonical(p["semantic"]) for p in left[1:]) == sorted(canonical(p["semantic"]) for p in right[1:]),
               "source_margin": frozen_score - config["threshold"],
               "same_best_query_onset_anchors": common_anchors,
               "best_inspected_acoustic_fields_exact_equal": a["semantic"] == b["semantic"],
               "retained_acoustic_path_multiset_exact_equal": left_signatures == right_signatures,
               "shared_exact_retained_acoustic_signatures": len(set(left_signatures) & set(right_signatures)),
               "best_global_transform_exact_equal": a["semantic"]["global_transform"] == b["semantic"]["global_transform"],
               "true_best_global_pitch_shift": a["semantic"]["global_transform"][0],
               "candidate_best_global_pitch_shift": b["semantic"]["global_transform"][0],
               "true_best_timing_scale": a["semantic"]["global_transform"][1],
               "candidate_best_timing_scale": b["semantic"]["global_transform"][1],
               "true_best_timing_offset_s": a["semantic"]["global_transform"][2],
               "candidate_best_timing_offset_s": b["semantic"]["global_transform"][2],
               "best_matched_acoustic_fields_exact_equal": a["semantic"]["matched"] == b["semantic"]["matched"],
               "best_missing_acoustic_fields_exact_equal": a["semantic"]["missing"] == b["semantic"]["missing"],
               "best_missing_anchor_regions_equal": missing_regions(a) == missing_regions(b),
               "best_inserted_acoustic_fields_exact_equal": a["semantic"]["inserted"] == b["semantic"]["inserted"],
               **deltas}
        pair_rows.append(row)
    assert len(pair_rows) == 68 and len(path_details) == 85 and len(path_rows) == 112
    query_rows = []
    for qid, metadata in sorted(data["query_metadata"].items()):
        pairs = [p for p in pair_rows if p["query_id"] == qid]
        excluded = sorted(set(range(len(desc[qid]["event_onset_s"]))) - set(eligibility[qid]))
        query_rows.append({**metadata, "maximum_pair_n": len(pairs), "available_pair_n": len(pairs),
            "raw_cached_query_event_n": len(desc[qid]["event_onset_s"]), "saved_eligible_query_event_n": len(eligibility[qid]),
            "query_events_outside_saved_eligible_set": excluded,
            "excluded_event_pitch_spans_cents": [float(desc[qid]["event_pitch_span_cents"][i]) for i in excluded],
            "pairs_best_acoustic_fields_equal": sum(p["best_inspected_acoustic_fields_exact_equal"] for p in pairs),
            "pairs_best_matched_fields_equal": sum(p["best_matched_acoustic_fields_exact_equal"] for p in pairs),
            "pairs_missing_anchor_regions_different": sum(not p["best_missing_anchor_regions_equal"] for p in pairs),
            "pairs_global_transform_different": sum(not p["best_global_transform_exact_equal"] for p in pairs),
            "true_saved_path_count": len(path_details[qid, metadata["true_reference"]]),
            "candidate_saved_path_count_total": sum(p["candidate_path_count"] for p in pairs),
            "source_margin": pairs[0]["source_margin"], "frozen_outcome": "none"})
        assert pairs[0]["source_margin"] < 0
    equality_fields = [key for key in pair_rows[0] if key.endswith("equal") or key == "same_best_query_onset_anchors"]
    difference_fields = [key for key in pair_rows[0] if key.endswith("max_abs_difference")]
    comparisons = {}
    for field in difference_fields:
        values = [p[field] for p in pair_rows if p[field] is not None]
        comparisons[field] = {"comparable_pairs": len(values), "exactly_zero": sum(x == 0 for x in values),
                              "nonzero": sum(x != 0 for x in values), "min": min(values), "max": max(values)}
    best_details = [paths[0] for paths in path_details.values()]
    best_pitch_max = max(abs(x) for p in best_details for x in p["pitch_residuals"])
    best_timing_max = max(abs(x) for p in best_details for x in p["timing_residuals_s"])
    strata = []
    for dimension in ("group_id", "family"):
        for value in sorted({q[dimension] for q in query_rows}):
            qs = [q for q in query_rows if q[dimension] == value]
            selected_ids = {q["query_id"] for q in qs}
            ps = [p for p in pair_rows if p["query_id"] in selected_ids]
            strata.append({"stratum": dimension, "value": value, "query_n": len(qs), "maximum_pair_n": len(ps),
                           **{"pairs_"+field: sum(p[field] for p in ps) for field in equality_fields}})
    summary = {"selected_queries": 17, "maximum_pairs": 68, "evidence_records": 85, "saved_paths": 112,
        "saved_alternative_paths_beyond_best": len(path_rows) - len(path_details),
        "records_with_retained_alternatives": sum(len(v) > 1 for v in path_details.values()),
        "true_records_with_retained_alternatives": sum(len(path_details[q, m["true_reference"]]) > 1 for q,m in data["query_metadata"].items()),
        "acoustic_descriptions": len(desc), "all_selected_pairs_available": True,
        "query_eligible_event_counts": dict(Counter(q["saved_eligible_query_event_n"] for q in query_rows)),
        "queries_with_cached_events_outside_saved_eligible_set": sum(bool(q["query_events_outside_saved_eligible_set"]) for q in query_rows),
        "pair_equality_counts": {field: sum(p[field] for p in pair_rows) for field in equality_fields},
        "pair_difference_magnitudes": comparisons,
        "best_record_max_abs_pitch_residual_semitones": best_pitch_max,
        "best_record_max_abs_timing_residual_s": best_timing_max,
        "all_best_record_residuals_inside_original_deadzones": best_pitch_max <= .05 and best_timing_max <= .005,
        "frozen_threshold": config["threshold"], "all_selected_queries_rejected": True,
        "verification": {"saved_residual_loss_reconstruction_max_abs_error": max_error,
                         "best_feature_reconstruction_max_abs_error": max_feature_error,
                         "arithmetic_check_tolerance": 1e-12, "all_68_saved_scores_and_vectors_exactly_reconciled": True,
                         "frozen_source_and_config_hashes_match": True},
        "comparison_contract": "Best paths compare actual shared-query onset anchors. Signatures include measured reference/query events, saved transforms and residuals, plus mapped missing-event hypotheses; opaque IDs and reference-local indices are excluded. Missing hypotheses are ordered chronologically, not matched as physically identical events. Exact equality is used throughout; magnitudes are reported, without a new decision tolerance.",
        "limits": "Only stored best/retained paths and selected cached event fields are inspected. Missing-event locations/pitches are hypotheses from a memory, not observed query notes or physical causes. Differences do not prove correct memory or perceptual identity. Equality under selected fields is not full acoustic equality. No alternative path search, extraction, fit or decision change."}
    write_csv(args.out / "pair_comparisons.csv", pair_rows)
    write_csv(args.out / "query_summary.csv", query_rows)
    write_csv(args.out / "saved_paths.csv", path_rows)
    write_csv(args.out / "matched_correspondences.csv", match_rows)
    write_csv(args.out / "missing_event_hypotheses.csv", missing_rows)
    # Keep an explicit empty list if no saved path contains an inserted event.
    write_json(args.out / "inserted_query_events.json", inserted_rows)
    write_csv(args.out / "cached_events.csv", event_rows)
    write_csv(args.out / "group_family_summary.csv", strata)
    write_json(args.out / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
