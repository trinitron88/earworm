"""Independent stdlib-only check of the published census and all tied maxima.

Uses archived candidate scores directly and tuple projections for categories.
Does not import the analysis script or execute any experiment module.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def check(directory):
    root = Path(__file__).resolve().parents[3]
    prior = root / "review/experiment08/calibration-audit/completion-20260919"
    config = json.loads((root / "work/accounts_results/frozen_config.json").read_text())
    threshold = config["threshold"]
    keep = [i for i, name in enumerate(config["feature_names"]) if name not in ("cost", "mean_timing_loss")]
    source = [json.loads(line) for line in (prior / "candidate_evidence.jsonl").read_text().splitlines()]
    source = [q for q in source if q["split"] == "held_out"]
    scores = {(r["query_id"], r["candidate_id"]): float(r["support_logit"])
              for r in read_csv(prior / "results/candidate_scores.csv")}
    qrows = {r["query_id"]: r for r in read_csv(directory / "query_census.csv")}
    pairs = read_csv(directory / "maximum_pair_census.csv")
    prows = {(r["query_id"], r["candidate_id"]): r for r in pairs}
    assert len(prows) == len(pairs), "Duplicate query-candidate pair"
    expected_pairs = set()
    expected_categories, expected_outcomes = Counter(), Counter()
    exact_tie_queries = 0
    for q in source:
        qid = q["query_id"]
        qr = qrows[qid]
        # Sorting archived scores independently exposes every exact maximum.
        ordered = sorted(((scores[qid, rid], rid) for rid in q["absent_history"]), reverse=True)
        maximum = ordered[0][0]
        ids = {rid for value, rid in ordered if value == maximum}
        assert ids == set(json.loads(qr["exact_absent_max_ids"]))
        exact_tie_queries += len(ids) > 1
        ts = q["candidates"][q["true_reference"]]
        categories = []
        for rid in ids:
            expected_pairs.add((qid, rid))
            cs = q["candidates"][rid]
            if not ts["available"] or not cs["available"]:
                cat = "unavailable"
            elif tuple(ts["features"]) == tuple(cs["features"]):
                cat = "all_12_equal"
            elif tuple(ts["features"][i] for i in keep) == tuple(cs["features"][i] for i in keep):
                cat = "only_cost_timing_differ"
            else:
                cat = "other_differences"
            pr = prows[qid, rid]
            assert pr["category"] == cat
            categories.append(cat)
            expected_categories[cat] += 1
            if cat != "unavailable":
                assert json.loads(pr["true_features"]) == ts["features"]
                assert json.loads(pr["candidate_features"]) == cs["features"]
        for cat in ("all_12_equal", "only_cost_timing_differ", "other_differences", "unavailable"):
            assert int(qr["pair_n_" + cat]) == categories.count(cat)
            assert (qr["any_" + cat] == "True") == (cat in categories)
            assert (qr["all_" + cat] == "True") == (set(categories) == {cat})
        pos = {rid for rid in q["present_history"] if scores[qid, rid] >= threshold}
        neg = {rid for rid in q["absent_history"] if scores[qid, rid] >= threshold}
        outcome = "none" if not pos else "multiple_candidates" if len(pos) > 1 else "true_singleton" if q["true_reference"] in pos else "wrong_singleton"
        expected_outcomes[outcome] += 1
        assert qr["present_outcome"] == outcome
        assert set(json.loads(qr["accepted_present"])) == pos
        assert set(json.loads(qr["accepted_absent"])) == neg
    assert expected_pairs == set(prows)
    assert len(qrows) == len(source) == 576 and len({q["group_id"] for q in source}) == 16
    summary = json.loads((directory / "summary.json").read_text())["counts"]
    assert summary["max_pair_n"] == len(prows) == 632
    for cat, count in expected_categories.items():
        assert summary["pairs_" + cat] == count
    for outcome, count in expected_outcomes.items():
        assert summary["outcome_" + outcome] == count
    strata = read_csv(directory / "stratified_counts.csv")
    counts = [k for k, value in summary.items() if isinstance(value, int) and k != "group_n"]
    for dimension in {s["stratum"] for s in strata}:
        rows = [s for s in strata if s["stratum"] == dimension]
        # Every requested partition must recover each overall count, even with ties.
        for field in counts:
            assert sum(int(s[field]) for s in rows) == summary[field], (dimension, field)
    for item in json.loads((directory / "input_identifiers.json").read_text())["inputs"]:
        assert hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    return {"query_records_independently_checked": len(source), "maximum_pairs_independently_checked": len(prows),
            "all_exact_maxima_preserved": True, "duplicate_pairs": 0,
            "feature_categories_independently_matched": dict(expected_categories),
            "present_outcomes_independently_matched": dict(expected_outcomes),
            "tied_maximum_queries": exact_tie_queries, "stratification_partitions_reconcile": 5,
            "all_input_hashes_unchanged": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parent / "results")
    args = parser.parse_args()
    print(json.dumps(check(args.results), indent=2))
