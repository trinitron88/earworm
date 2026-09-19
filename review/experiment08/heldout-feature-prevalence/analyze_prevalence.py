"""Descriptive census of published saved evidence. No experiment imports or fitting.

Run from any directory with Python 3 and NumPy:
  python analyze_prevalence.py --out /tmp/earworm-prevalence-results
The output directory must be new or empty. All inputs are repository-relative.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = "review/experiment08/calibration-audit/completion-20260919"
MATCHED = "review/experiment08/matched-pair-audit-e05-e21"
INPUTS = {
    "export": f"{PRIOR}/candidate_evidence.jsonl",
    "export_identifiers": f"{PRIOR}/input_identifiers.json",
    "scores": f"{PRIOR}/results/candidate_scores.csv",
    "margins": f"{PRIOR}/results/query_margins.csv",
    "config": "work/accounts_results/frozen_config.json",
    "trials": "review/experiment08/primary_trials.csv",
    "matched_scores": f"{MATCHED}/results/scores_and_margins.csv",
    "matched_inputs": f"{MATCHED}/saved_inputs.json",
}
CATEGORIES = ("all_12_equal", "only_cost_timing_differ", "other_differences", "unavailable")
OUTCOMES = ("true_singleton", "wrong_singleton", "multiple_candidates", "none")
NEAR = 1e-9  # Prior diagnostic, strict <; never used for feature equality/acceptance.


def load(name):
    return json.loads((ROOT / INPUTS[name]).read_text())


def csv_input(name):
    with (ROOT / INPUTS[name]).open(newline="") as stream:
        return list(csv.DictReader(stream))


def digest(path):
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


def score(evidence, config):
    # Only these saved acoustic-derived fields enter the frozen scorer.
    if not evidence["available"]:
        return -1e6
    return float(np.dot((np.asarray(evidence["features"]) - config["mean"]) / config["scale"],
                        config["coef"]) + config["intercept"])


def category(source, candidate, feature_names):
    if not source["available"] or not candidate["available"]:
        return "unavailable", []  # Never interpret sentinel-vector equality.
    differences = [name for name, left, right in zip(feature_names, source["features"], candidate["features"])
                   if left != right]
    if not differences:
        return "all_12_equal", differences
    if set(differences) <= {"cost", "mean_timing_loss"}:
        return "only_cost_timing_differ", differences
    return "other_differences", differences


def aggregate(queries, pairs):
    """Every query has equal weight in query counts; no tie duplication there."""
    result = {"query_n": len(queries), "group_n": len({q["group_id"] for q in queries}),
              "max_pair_n": len(pairs), "available_pair_n": sum(p["category"] != "unavailable" for p in pairs),
              "queries_all_max_pairs_available": sum(q["unavailable_pair_n"] == 0 for q in queries),
              "queries_with_tied_exact_absent_maxima": sum(q["exact_absent_max_n"] > 1 for q in queries),
              "queries_any_alternate_reference_max": sum(q["alternate_reference_is_exact_max"] for q in queries)}
    for cat in CATEGORIES:
        result["pairs_" + cat] = sum(p["category"] == cat for p in pairs)
        result["queries_any_" + cat] = sum(q["any_" + cat] for q in queries)
        result["queries_all_" + cat] = sum(q["all_" + cat] for q in queries)
    for name in OUTCOMES:
        result["outcome_" + name] = sum(q["present_outcome"] == name for q in queries)
    result.update(
        queries_any_ten_equal=sum(q["any_ten_equal"] for q in queries),
        queries_all_ten_equal=sum(q["all_ten_equal"] for q in queries),
        absent_false_accept_queries=sum(q["absent_false_accept"] for q in queries),
        true_vs_absent_max_score_near_queries=sum(q["true_vs_absent_max_score_near"] for q in queries),
        queries_with_extra_score_near_maxima=sum(q["score_near_absent_max_n"] > q["exact_absent_max_n"] for q in queries),
    )
    for field in ("true_margin", "absent_margin", "true_minus_absent_max"):
        values = [q[field] for q in queries]
        for name, value in zip(("min", "median", "max"), np.quantile(values, [0, .5, 1])):
            result[field + "_" + name] = float(value)
    assert sum(result["pairs_" + cat] for cat in CATEGORIES) == result["max_pair_n"]
    assert sum(result["outcome_" + outcome] for outcome in OUTCOMES) == result["query_n"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Output directory must be new or empty")
    args.out.mkdir(parents=True, exist_ok=True)
    config, identifiers = load("config"), load("export_identifiers")
    assert digest(ROOT / INPUTS["export"]) == identifiers["export"]["sha256"]
    config_hash = next(x["sha256"] for x in identifiers["original_inputs"] if x["path"] == INPUTS["config"])
    assert digest(ROOT / INPUTS["config"]) == config_hash
    names, threshold = config["feature_names"], config["threshold"]
    assert len(names) == 12 and len(set(names)) == 12
    exported = [json.loads(line) for line in (ROOT / INPUTS["export"]).read_text().splitlines()]
    raw = [q for q in exported if q["split"] == "held_out"]
    assert len(raw) == len({q["query_id"] for q in raw}) == 576
    assert len({q["group_id"] for q in raw}) == 16
    archived_scores = {(r["query_id"], r["candidate_id"]): r for r in csv_input("scores")}
    archived_margins = {r["query_id"]: r for r in csv_input("margins")}
    trials = {r["query_id"]: r for r in csv_input("trials") if r["method"] == "accounts"}
    pair_rows, query_rows, outcome_rows = [], [], []
    max_numpy_diff = max_scalar_diff = 0.0
    verified_candidates = 0
    for q in raw:
        qid, true_id = q["query_id"], q["true_reference"]
        candidates, present, absent = q["candidates"], q["present_history"], q["absent_history"]
        assert len(present) == len(set(present)) == 9 and len(absent) == len(set(absent)) == 9
        assert true_id in present and true_id not in absent
        assert set(candidates) == set(present) | set(absent)
        alternate = list(set(absent) - set(present))
        assert len(alternate) == 1
        scores = {}
        for rid, ev in candidates.items():
            archived = archived_scores[qid, rid]
            assert len(ev["features"]) == 12 and all(math.isfinite(x) for x in ev["features"])
            assert (archived["available"] == "True") == ev["available"]
            assert (archived["in_present_history"] == "True") == (rid in present)
            assert (archived["in_absent_history"] == "True") == (rid in absent)
            # Published round-trippable scores preserve the earlier arithmetic at boundaries.
            scores[rid] = float(archived["support_logit"])
            delta = abs(score(ev, config) - scores[rid])
            max_numpy_diff = max(max_numpy_diff, delta)
            assert delta == 0, (qid, rid, "frozen NumPy score differs from prior publication")
            scalar = (math.fsum((v-m)/s*w for v,m,s,w in zip(ev["features"], config["mean"], config["scale"], config["coef"]))
                      + config["intercept"]) if ev["available"] else -1e6
            max_scalar_diff = max(max_scalar_diff, abs(scalar - scores[rid]))
            verified_candidates += 1
        accepted_present = [rid for rid in present if scores[rid] >= threshold]
        accepted_absent = [rid for rid in absent if scores[rid] >= threshold]
        outcome = ("none" if not accepted_present else "multiple_candidates" if len(accepted_present) > 1
                   else "true_singleton" if accepted_present[0] == true_id else "wrong_singleton")
        mx = max(scores[rid] for rid in absent)
        exact_ids = [rid for rid in absent if scores[rid] == mx]
        near_ids = [rid for rid in absent if abs(scores[rid] - mx) < NEAR]
        true_score = scores[true_id]
        base = {key: q[key] for key in ("query_id", "group_id", "length", "family", "true_reference")}
        row = dict(base, true_available=candidates[true_id]["available"], alternate_reference=alternate[0],
                   alternate_reference_is_exact_max=alternate[0] in exact_ids,
                   exact_absent_max_ids=exact_ids, exact_absent_max_n=len(exact_ids),
                   score_near_absent_max_ids=near_ids, score_near_absent_max_n=len(near_ids),
                   true_score=true_score, absent_max_score=mx, true_margin=true_score-threshold,
                   absent_margin=mx-threshold, true_minus_absent_max=true_score-mx,
                   true_vs_absent_max_score_near=abs(true_score-mx) < NEAR,
                   present_outcome=outcome, accepted_present=accepted_present, accepted_absent=accepted_absent,
                   absent_false_accept=bool(accepted_absent))
        categories = []
        for rid in exact_ids:
            cat, differences = category(candidates[true_id], candidates[rid], names)
            categories.append(cat)
            pair_rows.append(dict(base, candidate_id=rid, candidate_is_alternate_reference=rid == alternate[0],
                                  true_available=candidates[true_id]["available"], candidate_available=candidates[rid]["available"],
                                  category=cat, differing_features=differences,
                                  true_features=candidates[true_id]["features"] if cat != "unavailable" else [],
                                  candidate_features=candidates[rid]["features"] if cat != "unavailable" else [],
                                  exact_max_tie_n=len(exact_ids), true_score=true_score, candidate_score=mx,
                                  true_margin=true_score-threshold, absent_margin=mx-threshold,
                                  true_minus_candidate=true_score-mx, present_outcome=outcome,
                                  absent_false_accept=bool(accepted_absent)))
        counts = Counter(categories)
        row["unavailable_pair_n"] = counts["unavailable"]
        for cat in CATEGORIES:
            row["pair_n_" + cat] = counts[cat]
            row["any_" + cat] = counts[cat] > 0
            row["all_" + cat] = counts[cat] == len(categories)
        row["any_ten_equal"] = any(c in CATEGORIES[:2] for c in categories)
        row["all_ten_equal"] = all(c in CATEGORIES[:2] for c in categories)
        query_rows.append(row)
        old = archived_margins[qid]
        for key in ("true_score", "absent_max_score", "true_margin", "absent_margin", "true_minus_absent_max"):
            assert row[key] == float(old[key]), (qid, key)
        assert exact_ids == old["absent_max_ids"].split("|")
        assert accepted_present == json.loads(trials[qid]["accepted_present"])
        assert accepted_absent == json.loads(trials[qid]["accepted_absent"])
        assert (outcome == "true_singleton") == (old["accepted_correct"] == "True")
        assert bool(accepted_absent) == (old["absent_false_accept"] == "True")
    assert max_scalar_diff < 1e-12  # Arithmetic verification only; not a classification tolerance.
    summary = aggregate(query_rows, pair_rows)
    assert summary["outcome_true_singleton"] == 164 and summary["absent_false_accept_queries"] == 0
    query_lookup = {q["query_id"]: q for q in query_rows}
    e21_checks = []
    for archived in csv_input("matched_scores"):
        qid = archived["query_id"]
        if not qid.startswith("e21_"):
            continue
        current = query_lookup[qid]
        for key in ("true_score", "absent_max_score", "true_margin", "absent_margin", "true_minus_absent_max"):
            assert current[key] == float(archived[key]), (qid, key)
        assert current["exact_absent_max_ids"] == archived["absent_max_ids"].split("|")
        expected = "only_cost_timing_differ" if "_a_" in qid else "other_differences"
        assert current["all_" + expected]
        e21_checks.append({"query_id": qid, "category": expected, "scores_margins_and_ids_exact": True})
    assert len(e21_checks) == 2
    raw_lookup = {q["query_id"]: q for q in raw}
    for previous in load("matched_inputs")["queries"]:
        q = previous["query"]
        if q["query_id"].startswith("e21_"):
            assert raw_lookup[q["query_id"]] == q, "e21 saved query/vector context changed"
    strata = []
    dimensions = [("group_id",), ("length",), ("family",), ("length", "family"), ("group_id", "length", "family")]
    for dim in dimensions:
        buckets = defaultdict(list)
        for q in query_rows:
            buckets[tuple(q[k] for k in dim)].append(q)
        for values, qs in sorted(buckets.items()):
            qids = {q["query_id"] for q in qs}
            ps = [p for p in pair_rows if p["query_id"] in qids]
            strata.append(dict(stratum="+".join(dim), group_id="", length="", family="",
                               **aggregate(qs, ps)))
            strata[-1].update(zip(dim, values))
    for cat in (*CATEGORIES, "ten_equal"):
        for relation in ("any", "all"):
            qs = [q for q in query_rows if q[relation + "_" + cat]]
            outcome_rows.append(dict(category=cat, query_rule=relation, total_query_n=576, matching_query_n=len(qs),
                                     **{"outcome_" + o: sum(q["present_outcome"] == o for q in qs) for o in OUTCOMES},
                                     absent_false_accept_queries=sum(q["absent_false_accept"] for q in qs)))
            for field in ("true_margin", "absent_margin", "true_minus_absent_max"):
                values = [q[field] for q in qs]
                stats = np.quantile(values, [0, .5, 1]) if values else [None] * 3
                for label, value in zip(("min", "median", "max"), stats):
                    outcome_rows[-1][field + "_" + label] = None if value is None else float(value)
    verification = {"held_out_queries": len(raw), "held_out_candidate_vectors": verified_candidates,
                    "groups": 16, "frozen_numpy_scores_exact": max_numpy_diff == 0,
                    "scalar_max_abs_difference": max_scalar_diff, "arithmetic_check_tolerance": 1e-12,
                    "previous_query_margins_and_exact_maxima_matched": 576,
                    "primary_present_and_absent_decisions_matched": 576,
                    "e21_matched_pair_crosschecks": e21_checks,
                    "export_hash_and_frozen_config_hash_match_prior_identifiers": True}
    write_csv(args.out / "query_census.csv", query_rows)
    write_csv(args.out / "maximum_pair_census.csv", pair_rows)
    write_csv(args.out / "stratified_counts.csv", strata)
    write_csv(args.out / "category_outcomes.csv", outcome_rows)
    write_json(args.out / "summary.json", {"frozen_threshold": threshold, "feature_order": names,
        "categories": {"all_12_equal": "Both available; every feature compares exactly equal.",
                       "only_cost_timing_differ": "Both available; other ten exactly equal; cost and/or mean_timing_loss differ.",
                       "other_differences": "Both available; at least one of the other ten differs.",
                       "unavailable": "True-source and/or tied maximum evidence unavailable; no feature equality inferred."},
        "denominators": "Pair counts include every exact absent-history maximum. Query any/all count each query once across all its exact maxima, including unavailable pairs; category-any columns can overlap. Ten-equal is the union of the first two categories. No tolerance in feature equality or acceptance.",
        "score_near_diagnostic": "Prior strict absolute score difference < 1e-9; reported separately and never used to select exact maxima, classify features, or decide acceptance.",
        "counts": summary, "verification": verification})
    write_json(args.out / "input_identifiers.json", {"base_main_commit": "1c695ffc33e00f239ac5b070696b8b1a2121ac59",
        "assignment_id": "earworm-heldout-feature-prevalence-v1", "instruction_comment_id": 5744179177,
        "inputs": [{"role": role, "path": path, "sha256": digest(ROOT / path), "bytes": (ROOT / path).stat().st_size}
                   for role, path in INPUTS.items()],
        "scoring_contract": "Only available/features enter frozen arithmetic; metadata routes evaluation and stratification only.",
        "provenance": "Uses the published compact export directly. This audit does not revalidate original omitted pair files or acoustic caches and does not assign an execution Git revision to the original experiment."})
    print(json.dumps({"counts": summary, "verification": verification}, indent=2))


if __name__ == "__main__":
    main()
