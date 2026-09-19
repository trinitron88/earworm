"""Export only the authorized saved records. No extraction or alignment execution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

PRIOR = "review/experiment08/calibration-audit/completion-20260919"
CENSUS = "review/experiment08/heldout-feature-prevalence"
EVENT_FIELDS = ["event_onset_s", "event_offset_s", "event_pitch_semitones",
                "event_pitch_span_cents", "event_phase_fraction", "event_bend_peak_cents"]
PATH_FIELDS = ["cost", "matched_pairs", "missing_reference", "inserted_query", "global_pitch_shift",
               "timing_scale", "timing_offset_s", "pitch_residual_semitones",
               "absolute_pitch_change_semitones", "onset_change_s", "timing_residual_s",
               "mean_pitch_loss", "exact_pitch_fraction", "mean_timing_loss"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    src, snap, out = args.source_root, args.snapshot_root, args.out
    out.mkdir(parents=True, exist_ok=True)
    for name in ("saved_inputs.json", "input_identifiers.json", "inventory.json"):
        if (out / name).exists():
            raise ValueError("Refusing to replace an existing export: " + name)
    config = json.loads((snap / "work/accounts_results/frozen_config.json").read_text())
    previous = json.loads((snap / PRIOR / "input_identifiers.json").read_text())
    inputs = []
    for rel in ("work/accounts_results/held_out_pairs.json", "work/accounts_results/frozen_config.json",
                "work/accounts_results/protocol.json"):
        expected = next(i["sha256"] for i in previous["original_inputs"] if i["path"] == rel)
        assert sha(src / rel) == expected, rel
        if (snap / rel).exists():
            assert sha(snap / rel) == expected, rel
        inputs.append({"path": rel, "sha256": expected, "bytes": (src / rel).stat().st_size})
    for name, digest in config["source_sha256"].items():
        assert sha(src / "work" / name) == digest == sha(snap / "work" / name)
    compact = snap / PRIOR / "candidate_evidence.jsonl"
    assert sha(compact) == previous["export"]["sha256"]
    compact_queries = {q["query_id"]: q for q in map(json.loads, compact.read_text().splitlines())}
    selection_path = snap / CENSUS / "results/maximum_pair_census.csv"
    expected = next(line.split()[0] for line in (snap / CENSUS / "CHECKSUMS.sha256").read_text().splitlines()
                    if line.endswith("  results/maximum_pair_census.csv"))
    assert sha(selection_path) == expected
    with selection_path.open(newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    selection = [{"census_data_row_1_based": i + 1, "query_id": r["query_id"],
                  "true_reference": r["true_reference"], "candidate_id": r["candidate_id"],
                  "category": r["category"], "source_score": float(r["true_score"]),
                  "candidate_score": float(r["candidate_score"])}
                 for i, r in enumerate(all_rows) if r["category"] == "all_12_equal"]
    assert len(selection) == len({(r["query_id"], r["candidate_id"]) for r in selection}) == 68
    query_ids = sorted({r["query_id"] for r in selection})
    assert len(query_ids) == 17
    original = json.loads((src / "work/accounts_results/held_out_pairs.json").read_text())
    records, inventory_records, query_metadata = {}, [], {}
    needed = set(query_ids)
    for qid in query_ids:
        q = compact_queries[qid]
        assert q["split"] == "held_out"
        query_metadata[qid] = {k: q[k] for k in ("query_id", "group_id", "length", "family", "true_reference")}
        rids = sorted({r["candidate_id"] for r in selection if r["query_id"] == qid} | {q["true_reference"]})
        records[qid] = {}
        for rid in rids:
            needed.add(rid)
            record = original.get(qid, {}).get(rid, {}).get("evidence")
            missing = []
            if record is None:
                missing = ["evidence record"]
            else:
                missing += [k for k in ("available", "features", "paths", "reference_events", "query_events") if k not in record]
                if not missing:
                    assert all(record[k] == v for k, v in q["candidates"][rid].items())
                    for index, path in enumerate(record["paths"]):
                        missing += [f"paths[{index}].{k}" for k in PATH_FIELDS if k not in path]
                    if not record["paths"]:
                        missing.append("retained paths empty")
            status = "available" if not missing else "unavailable"
            records[qid][rid] = {"status": status, "missing_fields": missing, "evidence": record}
            inventory_records.append({"query_id": qid, "reference_id": rid, "status": status,
                                      "missing_fields": missing, "retained_path_count": len(record.get("paths", [])) if record else 0})
    timings_path = src / "work/accounts_features/timings.json"
    timings = json.loads(timings_path.read_text())
    descriptions, description_inventory, digest_checks = {}, [], []
    for bid in sorted(needed):
        rel = f"work/accounts_features/{bid}.npz"
        path = src / rel
        if not path.exists():
            description_inventory.append({"block_id": bid, "status": "unavailable", "missing_fields": [rel]})
            continue
        with np.load(path, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        h = hashlib.sha256()
        for key in sorted(arrays):
            array = np.asarray(arrays[key])
            h.update(key.encode()); h.update(str(array.dtype).encode()); h.update(str(array.shape).encode()); h.update(array.tobytes())
        assert h.hexdigest() == timings[bid]["description_digest"], bid
        missing = [k for k in EVENT_FIELDS if k not in arrays]
        descriptions[bid] = {k: {"dtype": str(arrays[k].dtype), "values": arrays[k].tolist()}
                             for k in EVENT_FIELDS if k in arrays}
        description_inventory.append({"block_id": bid, "status": "unavailable" if missing else "available",
                                      "missing_fields": missing, "saved_event_count": len(arrays["event_onset_s"])})
        digest_checks.append({"block_id": bid, "full_description_digest": h.hexdigest(), "matched_original_timing_record": True})
        inputs.append({"path": rel, "sha256": sha(path), "bytes": path.stat().st_size})
    inputs.append({"path": "work/accounts_features/timings.json", "sha256": sha(timings_path), "bytes": timings_path.stat().st_size})
    write(out / "saved_inputs.json", {"selection": selection, "query_metadata": query_metadata,
                                      "records": records, "descriptions": descriptions})
    complete = all(r["status"] == "available" for r in inventory_records + description_inventory)
    write(out / "inventory.json", {"status": "complete" if complete else "missing_saved_evidence",
        "selected_queries": len(query_ids), "selected_maximum_pairs": len(selection),
        "selected_evidence_records": len(inventory_records), "selected_descriptions": len(needed),
        "saved_paths": sum(r["retained_path_count"] for r in inventory_records),
        "evidence_records": inventory_records, "acoustic_descriptions": description_inventory,
        "scope_limit": "Only previously saved best/retained paths and six event arrays are exported. Unretained paths, frame streams, waveforms and unscoped candidate records are not exported or regenerated."})
    write(out / "input_identifiers.json", {"assignment_id": "earworm-equal-vector-alignments-v1",
        "instruction_comment_ids": [5744506474, 5744608819], "base_main_commit": "536f314b10b8d1d4a0cbb14a92caef9616157b47",
        "original_execution_git_revision": None, "original_inputs": inputs,
        "frozen_source_sha256": config["source_sha256"], "original_description_digest_checks": digest_checks,
        "selection_source": {"path": str(Path(CENSUS) / "results/maximum_pair_census.csv"), "sha256": sha(selection_path),
                             "selection_rule": "category exactly all_12_equal; retain every row and its original one-based data-row index"},
        "prior_compact_export": {"path": str(Path(PRIOR) / "candidate_evidence.jsonl"), "sha256": sha(compact)},
        "selected_export": {"path": "saved_inputs.json", "sha256": sha(out / "saved_inputs.json"), "bytes": (out / "saved_inputs.json").stat().st_size},
        "method": "Exact selection of saved evidence records and typed event arrays. No audio processing, extraction, path search, scoring-rule change or experiment execution.",
        "provenance_limit": "File hashes identify the saved inputs used now and agree with the preceding export where recorded; they are not new pre-run commitments. Full cached-description digests match original extraction timing records. Publication commits are not original execution revisions."})
    print(json.dumps({"inventory_complete": complete, "queries": len(query_ids), "pairs": len(selection),
                      "records": len(inventory_records), "paths": sum(r["retained_path_count"] for r in inventory_records),
                      "descriptions": len(needed), "export_bytes": (out / "saved_inputs.json").stat().st_size}))


if __name__ == "__main__":
    main()
