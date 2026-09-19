"""Lossless typed export of existing frames within ten fixed, previously saved event bounds."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

PREVIOUS = "review/experiment08/equal-vector-alignment-audit"
FIELDS = ["frame_time_s", "frame_rms", "frame_energy_dbfs", "frame_voiced", "frame_pitch_hz",
          "frame_spectral_peak_hz", "frame_phase_refined", "frame_spectral_centroid_hz"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def pack(array):
    """Keep dtype and exact nonfinite bytes; JSON null is not an interpolated pitch."""
    a = np.ascontiguousarray(array)
    values, nonfinite = [], []
    for i, value in enumerate(a):
        if np.isfinite(value):
            values.append(value.item())
        else:
            values.append(None)
            nonfinite.append({"index": i, "kind": "nan" if np.isnan(value) else "+inf" if value > 0 else "-inf",
                              "raw_bytes_hex": a[i:i+1].tobytes().hex()})
    result = {"dtype": str(a.dtype), "dtype_str": a.dtype.str, "shape": list(a.shape), "values": values,
              "nonfinite": nonfinite, "raw_bytes_sha256": hashlib.sha256(a.tobytes()).hexdigest()}
    # Round-trip every selected value, including the original NaN payload, before publishing.
    restored = np.asarray([0 if x is None else x for x in values], dtype=a.dtype)
    for item in nonfinite:
        restored.view(np.uint8).reshape(-1, a.dtype.itemsize)[item["index"]] = np.frombuffer(bytes.fromhex(item["raw_bytes_hex"]), dtype=np.uint8)
    assert restored.tobytes() == a.tobytes()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    src, snap, out = args.source_root, args.snapshot_root, args.out
    out.mkdir(parents=True, exist_ok=True)
    for name in ("saved_frames.json", "input_identifiers.json", "inventory.json", "memory_expectations.csv"):
        if (out / name).exists():
            raise ValueError("Refusing to overwrite existing export: " + name)
    prev = snap / PREVIOUS
    prior_ids = json.loads((prev / "input_identifiers.json").read_text())
    prior_data = json.loads((prev / "saved_inputs.json").read_text())
    assert sha(prev / "saved_inputs.json") == prior_ids["selected_export"]["sha256"]
    with (prev / "results/query_summary.csv").open(newline="") as stream:
        qs = list(csv.DictReader(stream))
    selected = [(q, i) for q in qs for i in json.loads(q["query_events_outside_saved_eligible_set"])]
    assert len(selected) == len({q["query_id"] for q, _ in selected}) == 10
    assert all(q["family"] == "merged" for q, _ in selected)
    config = json.loads((snap / "work/accounts_results/frozen_config.json").read_text())
    for name, digest in config["source_sha256"].items():
        assert sha(src / "work" / name) == digest == sha(snap / "work" / name)
    timings_path = src / "work/accounts_features/timings.json"
    timings = json.loads(timings_path.read_text())
    assert sha(timings_path) == next(x["sha256"] for x in prior_ids["original_inputs"] if x["path"] == "work/accounts_features/timings.json")
    events, inventory, inputs, checks = [], [], [], []
    for q, event_index in selected:
        qid = q["query_id"]
        prior_desc = prior_data["descriptions"][qid]
        on = prior_desc["event_onset_s"]["values"][event_index]
        off = prior_desc["event_offset_s"]["values"][event_index]
        rel = f"work/accounts_features/{qid}.npz"
        path = src / rel
        expected_hash = next(x["sha256"] for x in prior_ids["original_inputs"] if x["path"] == rel)
        entry = {"query_id": qid, "event_index": event_index, "onset_s": on, "offset_s": off,
                 "interior_start_s": on + .018, "interior_end_s": off - .018}
        if not path.exists():
            inventory.append({**entry, "status": "unavailable", "missing": [rel]})
            continue
        assert sha(path) == expected_hash, qid
        with np.load(path, allow_pickle=False) as z:
            cache = {k: z[k] for k in z.files}
        h = hashlib.sha256()
        for key in sorted(cache):
            value = np.asarray(cache[key]);h.update(key.encode());h.update(str(value.dtype).encode());h.update(str(value.shape).encode());h.update(value.tobytes())
        assert h.hexdigest() == timings[qid]["description_digest"]
        assert float(cache["event_onset_s"][event_index]) == on and float(cache["event_offset_s"][event_index]) == off
        missing = [key for key in FIELDS if key not in cache]
        if "frame_time_s" in missing:
            inventory.append({**entry, "status": "unavailable", "missing": missing})
            continue
        times = cache["frame_time_s"].astype(float)
        assert np.isfinite(times).all() and np.all(np.diff(times) > 0)
        indices = np.flatnonzero((times >= on) & (times <= off))
        if len(indices):
            assert np.array_equal(indices, np.arange(indices[0], indices[-1] + 1))
        arrays = {}
        for key in FIELDS:
            if key not in cache:
                continue
            assert cache[key].ndim == 1 and len(cache[key]) == len(times), key
            arrays[key] = pack(cache[key][indices])
        entry.update(original_frame_count=len(times), original_frame_indices=indices.tolist(),
                     adjacent_frame_before_s=float(times[indices[0]-1]) if len(indices) and indices[0] else None,
                     adjacent_frame_after_s=float(times[indices[-1]+1]) if len(indices) and indices[-1]+1 < len(times) else None,
                     arrays=arrays, absent_arrays=missing)
        events.append(entry)
        inventory.append({k:v for k,v in entry.items() if k not in ("arrays", "original_frame_indices")})
        inventory[-1].update(status="available" if not missing and len(indices) else "partial", in_bound_frame_count=len(indices),
                             array_inventory={key: {"present": key in arrays, "dtype": arrays[key]["dtype"] if key in arrays else None,
                                                   "nonfinite_count": len(arrays[key]["nonfinite"]) if key in arrays else None} for key in FIELDS})
        inputs.append({"path": rel, "sha256": expected_hash, "bytes": path.stat().st_size})
        checks.append({"query_id": qid, "full_description_digest": h.hexdigest(), "matched_original_timing_record": True})
    for rel in ("work/accounts_features/timings.json", "work/accounts_results/protocol.json", "work/accounts_results/frozen_config.json"):
        inputs.append({"path": rel, "sha256": sha(src / rel), "bytes": (src / rel).stat().st_size})
    selected_ids = {q["query_id"] for q, _ in selected}
    with (prev / "results/missing_event_hypotheses.csv").open(newline="") as stream:
        reader = csv.DictReader(stream); fieldnames = reader.fieldnames
        expectations = [dict(source_data_row_1_based=i+1, **row) for i,row in enumerate(reader) if row["query_id"] in selected_ids]
    with (out / "memory_expectations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_data_row_1_based"] + fieldnames, lineterminator="\n")
        writer.writeheader();writer.writerows(expectations)
    write(out / "saved_frames.json", {"events": events, "fields": FIELDS,
        "selection": "All saved frames with original timestamps in inclusive cached [onset, offset]. No samples removed within bounds. Interior [onset+.018, offset-.018] is context only.",
        "nonfinite_encoding": "Null values are original nonfinite samples, with kind and exact bytes recorded. Missing arrays are listed separately; no interpolation."})
    write(out / "inventory.json", {"selected_events": 10, "exported_events": len(events),
        "in_bound_frames": sum(len(e["original_frame_indices"]) for e in events),
        "status": "complete" if len(events) == 10 and all(e["status"] == "available" for e in inventory) else "missing_or_partial",
        "events": inventory, "memory_expectation_rows": len(expectations)})
    previous_inputs = ["input_identifiers.json", "saved_inputs.json", "results/query_summary.csv", "results/missing_event_hypotheses.csv"]
    write(out / "input_identifiers.json", {"assignment_id": "earworm-excluded-event-frame-timelines-v1", "instruction_comment_id": 5744920500,
        "base_main_commit": "a818d59f86cd8540399ea49f743d2d1bb0fb2736", "original_execution_git_revision": None,
        "original_inputs": inputs, "frozen_source_sha256": config["source_sha256"], "original_description_digest_checks": checks,
        "prior_audit_inputs": [{"path": str(Path(PREVIOUS)/name), "sha256": sha(prev/name)} for name in previous_inputs],
        "exports": [{"path": name, "sha256": sha(out/name), "bytes": (out/name).stat().st_size} for name in ("saved_frames.json", "inventory.json", "memory_expectations.csv")],
        "method": "Select existing typed array samples only; preserve original frame indices, dtypes, all values and nonfinite bits. Expectations copied to a separate table with source-row mapping. No extraction, boundary adjustment, interpolation, segmentation, path search, new feature/scorer or decision change.",
        "provenance_limit": "Original caches are not published in full; their hashes match the preceding audit and full-description digests match original timing records. Publication commits are not original execution revisions."})
    print(json.dumps({"events": len(events), "frames": sum(len(e["original_frame_indices"]) for e in events),
                      "expectation_rows": len(expectations), "export_bytes": (out/"saved_frames.json").stat().st_size}))


if __name__ == "__main__":
    main()
