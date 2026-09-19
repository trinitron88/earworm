"""Independent standard-library verification of scope, saved arithmetic and pair comparisons."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def event(d, i):
    return tuple(d[k]["values"][i] for k in ("event_onset_s", "event_offset_s", "event_pitch_semitones"))


def descriptor(path, rd, qd):
    """Tuple representation omits IDs/indices; values share the query time coordinate."""
    shift, scale, offset = (path[k] for k in ("global_pitch_shift", "timing_scale", "timing_offset_s"))
    pairs = path["matched_pairs"]
    match = []
    for j, (ri, qi) in enumerate(pairs):
        r, q = event(rd, ri), event(qd, qi)
        match.append((r, q, scale*r[0]+offset, scale*r[1]+offset, r[2]+shift,
                      path["pitch_residual_semitones"][j], path["timing_residual_s"][j],
                      path["absolute_pitch_change_semitones"][j], path["onset_change_s"][j]))
    missing = []
    for ri in path["missing_reference"]:
        r = event(rd, ri)
        earlier = [event(qd, q)[0] for a, q in pairs if event(rd, a)[0] < r[0]]
        later = [event(qd, q)[0] for a, q in pairs if event(rd, a)[0] > r[0]]
        missing.append((r, scale*r[0]+offset, scale*r[1]+offset, r[2]+shift,
                        r[2]-event(rd, pairs[0][0])[2], earlier[-1] if earlier else None, later[0] if later else None))
    return ((shift, scale, offset), tuple(match), tuple(missing), tuple(event(qd, qi) for qi in path["inserted_query"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=HERE / "results")
    args = parser.parse_args()
    data = json.loads((HERE / "saved_inputs.json").read_text())
    identifiers = json.loads((HERE / "input_identifiers.json").read_text())
    assert hashlib.sha256((HERE / "saved_inputs.json").read_bytes()).hexdigest() == identifiers["selected_export"]["sha256"]
    census = csv_rows(ROOT / identifiers["selection_source"]["path"])
    expected = {(r["query_id"], r["true_reference"], r["candidate_id"]) for r in census if r["category"] == "all_12_equal"}
    selection = {(r["query_id"], r["true_reference"], r["candidate_id"]) for r in data["selection"]}
    assert selection == expected and len(selection) == len(data["selection"]) == 68
    for r in data["selection"]:
        old = census[r["census_data_row_1_based"]-1]
        assert all(r[k] == old[k] for k in ("query_id", "true_reference", "candidate_id", "category"))
    desc, records = data["descriptions"], data["records"]
    summaries = {}
    max_error = 0.0
    path_n = 0
    for qid, rr in records.items():
        for rid, record in rr.items():
            e = record["evidence"]
            assert record["status"] == "available" and e["available"]
            summaries[qid, rid] = []
            for path in e["paths"]:
                path_n += 1
                pairs = path["matched_pairs"]
                assert all(a[0] < b[0] and a[1] < b[1] for a,b in zip(pairs,pairs[1:]))
                pl, tl = [], []
                for j, (ri, qi) in enumerate(pairs):
                    r, q = event(desc[rid], ri), event(desc[qid], qi)
                    pitch = q[2]-r[2]-path["global_pitch_shift"]
                    timing = q[0]-path["timing_scale"]*r[0]-path["timing_offset_s"]
                    max_error = max(max_error, abs(pitch-path["pitch_residual_semitones"][j]),
                                    abs(timing-path["timing_residual_s"][j]),
                                    abs(q[2]-r[2]-path["absolute_pitch_change_semitones"][j]),
                                    abs(q[0]-r[0]-path["onset_change_s"][j]))
                    pl.append(max(abs(pitch)-.05, 0)/2); tl.append(max(abs(timing)-.005, 0)*2)
                cost = (math.fsum(pl)+math.fsum(tl)+.7*(len(path["missing_reference"])+len(path["inserted_query"]))) / max(e["reference_events"],e["query_events"])
                max_error = max(max_error, abs(cost-path["cost"]), abs(math.fsum(pl)/len(pl)-path["mean_pitch_loss"]), abs(math.fsum(tl)/len(tl)-path["mean_timing_loss"]))
                summaries[qid, rid].append(descriptor(path, desc[rid], desc[qid]))
    assert path_n == 112 and len(summaries) == 85 and max_error < 1e-12
    table = csv_rows(args.results / "pair_comparisons.csv")
    assert {(r["query_id"],r["true_reference"],r["candidate_id"]) for r in table} == selection and len(table) == 68
    counts = {"best_equal": 0, "same_transform": 0, "same_matched_fields": 0, "same_missing_fields": 0,
              "same_missing_anchor_regions": 0, "same_retained_path_multiset": 0}
    for row in table:
        qid, true, rid = row["query_id"], row["true_reference"], row["candidate_id"]
        a, b = summaries[qid,true], summaries[qid,rid]
        assert records[qid][true]["evidence"]["features"] == records[qid][rid]["evidence"]["features"]
        checks = {"best_inspected_acoustic_fields_exact_equal": a[0] == b[0],
                  "best_global_transform_exact_equal": a[0][0] == b[0][0],
                  "best_matched_acoustic_fields_exact_equal": a[0][1] == b[0][1],
                  "best_missing_acoustic_fields_exact_equal": a[0][2] == b[0][2],
                  "best_inserted_acoustic_fields_exact_equal": a[0][3] == b[0][3],
                  "best_missing_anchor_regions_equal": [m[-2:] for m in a[0][2]] == [m[-2:] for m in b[0][2]],
                  "retained_acoustic_path_multiset_exact_equal": sorted(map(repr,a)) == sorted(map(repr,b)),
                  "retained_alternatives_only_multiset_equal": sorted(map(repr,a[1:])) == sorted(map(repr,b[1:])),
                  "same_best_query_onset_anchors": [m[1][0] for m in a[0][1]] == [m[1][0] for m in b[0][1]]}
        for field, expected_value in checks.items():
            assert (row[field] == "True") == expected_value, (qid,rid,field)
        assert int(row["true_path_count"]) == len(a) and int(row["candidate_path_count"]) == len(b)
        for field, key in [("best_equal", "best_inspected_acoustic_fields_exact_equal"),
                           ("same_transform", "best_global_transform_exact_equal"),
                           ("same_matched_fields", "best_matched_acoustic_fields_exact_equal"),
                           ("same_missing_fields", "best_missing_acoustic_fields_exact_equal"),
                           ("same_missing_anchor_regions", "best_missing_anchor_regions_equal"),
                           ("same_retained_path_multiset", "retained_acoustic_path_multiset_exact_equal")]:
            counts[field] += checks[key]
    qs = csv_rows(args.results / "query_summary.csv")
    assert len(qs) == 17 and sum(int(q["maximum_pair_n"]) for q in qs) == 68
    group_rows = csv_rows(args.results / "group_family_summary.csv")
    for dim in ("group_id", "family"):
        assert sum(int(r["query_n"]) for r in group_rows if r["stratum"] == dim) == 17
        assert sum(int(r["maximum_pair_n"]) for r in group_rows if r["stratum"] == dim) == 68
    print(json.dumps({"selected_queries":17,"selected_pairs":68,"saved_records":85,"saved_paths":path_n,
        "selection_exactly_matches_frozen_census":True,"pair_semantics_independently_verified":True,
        "independent_equality_counts":counts,"scalar_saved_arithmetic_max_abs_error":max_error,
        "arithmetic_verification_tolerance":1e-12,"group_family_counts_reconcile":True},indent=2))


if __name__ == "__main__":
    main()
