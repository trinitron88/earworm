"""Read-only verification of the aborted panel's saved artifacts.

No generators, matchers, probes, models or experiment runners are imported or
called. This script reads saved files and writes only its validation receipt.
It validates the retained partial archive, not the unavailable failing input.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import time

import numpy as np

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def read_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def validate():
    began = time.monotonic()
    started = datetime.now(timezone.utc).isoformat()
    base = ROOT / "inputs" / "panel"
    failure_path = base / "construction-failure.json"
    failure = read_json(failure_path)
    assert failure["status"] == "invalid-construction"
    assert failure["current"] == "novel-20260926-04--unchanged"
    assert failure["message"] == "Unintended complete source-equivalent 12-event occurrence in history"
    assert failure["exception"] == "ValueError"
    assert failure["candidate_readouts"] == 0
    assert failure["replacements_attempted"] == 0
    assert len(failure["completed_sessions"]) == 35
    hashes = {p.relative_to(ROOT).as_posix(): sha(p)
              for p in (failure_path, base / "generation-manifest.json")}
    counts = Counter()
    family_counts = Counter()
    cell_counts = Counter()
    stratum_counts = Counter()
    saved_sessions = []
    for session in failure["completed_sessions"]:
        directory = base / session["path"]
        assert directory.parent == base and directory.name == session["session_id"]
        assert set(session["files"]) == {"rows.npz", "exact-events.npz", "evaluatorlabels.json"}
        for name, evidence in session["files"].items():
            path = directory / name
            digest = sha(path)
            assert digest == evidence["sha256"], str(path)
            assert path.stat().st_size == evidence["bytes"], str(path)
            hashes[path.relative_to(ROOT).as_posix()] = digest
            counts["saved_file_hashes"] += 1
        rows = read_npz(directory / "rows.npz")
        exact = read_npz(directory / "exact-events.npz")
        labels = read_json(directory / "evaluatorlabels.json")
        assert set(rows) == {"t", "unit", "rms", "clean", "available_at"}
        assert set(exact) == {"events", "available_at"}
        events = exact["events"]
        t = rows["t"]
        assert events.ndim == 2 and events.shape[1] == 3
        assert len(events) == session["events"]
        assert np.isfinite(events).all() and np.all(events[:, 1] > events[:, 0])
        assert np.all(events[1:, 0] >= events[:-1, 1] - 1e-9)
        assert np.all((events[:, 2] >= 0) & (events[:, 2] < 128))
        assert np.all(events[:, 2] == np.floor(events[:, 2]))
        assert np.array_equal(exact["available_at"], np.ceil(events[:, 1]))
        assert len(t) == session["rows"]
        assert np.allclose(t, np.arange(len(t)) * 0.1 + 0.05, rtol=0, atol=1e-12)
        assert np.array_equal(rows["unit"], np.floor(t))
        assert np.array_equal(rows["available_at"], rows["unit"] + 1)
        assert rows["clean"].shape == (len(t), 129)
        assert rows["clean"].dtype == np.float32
        assert np.isin(rows["clean"], [0, 1]).all()
        assert np.all(rows["clean"].sum(axis=1) == 1)
        # Inspect each SAVED center against SAVED events; do not regenerate any
        # event stream, material, clean observation array or candidate output.
        for i, center in enumerate(t):
            present = events[(events[:, 0] <= center) & (center < events[:, 1])]
            assert len(present) <= 1
            expected_pitch = int(present[0, 2]) if len(present) else 128
            assert int(rows["clean"][i].argmax()) == expected_pitch
            assert rows["rms"][i] == int(expected_pitch != 128)
        assert labels["session_id"] == session["session_id"]
        assert labels["split"] == "development"
        assert labels["group"] == session["group"]
        assert labels["cell"] == session["cell"]
        assert labels["stratum"] == session["stratum"]
        assert labels["decision_seconds"] == session["decision_seconds"]
        assert len(t) == labels["decision_seconds"] * 10
        if labels["stratum"] == "bach":
            provenance = labels["source_provenance"]
            assert provenance["note_indices"] == list(range(24, 36))
            assert provenance["previous_note_indices"] == list(range(12))
            assert not set(provenance["note_indices"]) & set(provenance["previous_note_indices"])
            assert provenance["historical_range_overlap"] is False
            counts["bach_provenance_records"] += 1
        active_last = np.flatnonzero(rows["rms"] > 1e-4)[-1]
        query_indices = np.arange(active_last - 19, active_last + 1)
        assert np.array_equal(query_indices, labels["observed_query_row_indices"])
        assert np.array_equal(t[query_indices], labels["observed_query_centers"])
        assert np.allclose(labels["observed_query_support"],
                           [t[query_indices[0]] - 0.05, t[query_indices[-1]] + 0.05], rtol=0, atol=1e-12)
        if session["cell"] == "inventory_foil":
            assert labels["inventory_preserved"] is True
            assert sorted(x[2] for x in labels["source_events"]) == sorted(x[2] for x in labels["query_events"])
        if session["cell"] in ("inventory_foil", "near_foil"):
            assert labels["decisive_observed_difference_centers"]
            assert set(labels["decisive_observed_difference_centers"]) <= set(labels["observed_query_centers"])
        counts["sessions"] += 1
        counts["sample_centers_checked"] += len(t)
        counts["event_rows"] += len(events)
        family_counts[session["group"]] += 1
        cell_counts[session["cell"]] += 1
        stratum_counts[session["stratum"]] += 1
        saved_sessions.append(session["session_id"])
    assert counts["saved_file_hashes"] == 105
    assert counts["sample_centers_checked"] == 14010
    assert counts["event_rows"] == 4270
    assert counts["bach_provenance_records"] == 20
    assert len(family_counts) == 7 and set(family_counts.values()) == {5}
    failed_dir = base / failure["current"]
    assert not failed_dir.exists()
    assert not (base / "input-manifest.json").exists()
    actual_files = {p.relative_to(ROOT).as_posix() for p in base.rglob("*") if p.is_file()}
    assert actual_files == set(hashes), "Unexpected or omitted saved panel input"

    # Count retained qualification receipts without re-running their probes.
    ledger_path = ROOT / "qualification" / "ledger.json"
    ledger = read_json(ledger_path)
    calls = ledger["calls"]
    assert len(calls) == 29
    passed = [c for c in calls if c["passed"]]
    failed = [c for c in calls if not c["passed"]]
    assert len(passed) == 28 and len(failed) == 1
    assert failed[0]["name"] == "G-scale-lower-bound"
    assert failed[0]["error"] == "AssertionError"
    assert ledger["fixture_correction"]["after_call"] == 21
    process_expectations = {
        "process-D-full": True, "process-G-full": True,
        "process-G-exact-full": True, "process-G-recent": False,
        "process-G-exact-removed": False,
    }
    process_calls = [c for c in calls if c["name"].startswith("process-")]
    assert {c["name"] for c in process_calls} == set(process_expectations)
    process_receipts = []
    qualification_hashes = {ledger_path.relative_to(ROOT).as_posix(): sha(ledger_path)}
    for call in process_calls:
        directory = ROOT / "qualification" / call["name"]
        response = read_json(directory / "response.json")
        arrivals = read_json(directory / "arrivals.json")
        completed = read_json(directory / "completed.json")
        assert call["passed"] and completed["returncode"] == 0
        assert response == call["answer"]
        assert response["accepted"] is process_expectations[call["name"]]
        assert len(arrivals) == 10
        assert [r["unit"] for r in arrivals] == list(range(10))
        assert all(r["simulated_available_at"] == r["unit"] + 1 for r in arrivals)
        assert all(len(r["recent_units"]) <= 4 for r in arrivals)
        assert response["persistent_replacements"] == 0
        assert response["predictor_accessible_state_bytes"] <= 8 * 1024**2
        assert response["actual_output_availability_upper_bound"] >= response["prediction_finished_monotonic"]
        assert response["prediction_finished_monotonic"] >= response["parent_prediction_request_monotonic"]
        if response["mode"] == "recent":
            assert response["kept_units"] == [6, 7, 8, 9]
        if response["mode"] == "removed":
            assert response["removed_units"] == [0, 1, 2]
            assert not set(response["kept_units"]) & set(response["removed_units"])
        for name in ("started.json", "response.json", "arrivals.json", "completed.json"):
            p = directory / name
            qualification_hashes[p.relative_to(ROOT).as_posix()] = sha(p)
        process_receipts.append({"name": call["name"], "accepted": response["accepted"],
                                 "mode": response["mode"], "arrivals": len(arrivals),
                                 "retained_units": response["kept_units"],
                                 "predictor_accessible_state_bytes": response["predictor_accessible_state_bytes"],
                                 "recorded_checks_passed": True})
    return {
        "schema": "correspondence-reference-saved-input-validation-v1",
        "validation_status": "pass", "study_status": "INVALID-construction",
        "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": time.monotonic() - began,
        "validator_sha256": sha(Path(__file__)),
        "counts": dict(counts), "per_family_sessions": dict(family_counts),
        "per_cell_sessions": dict(cell_counts), "per_stratum_sessions": dict(stratum_counts),
        "saved_sessions": saved_sessions, "input_sha256": hashes,
        "total_panel_files_hashed": len(hashes),
        "failed_session": failure["current"], "failed_session_artifacts_present": False,
        "witness_limitation": "The failure receipt preserves the condition and stopped session but not the failing source/history arrays or duplicate-window indices. This validator cannot independently name or verify the offending collision. It does not regenerate the material. The guard compares signed pitch intervals, not complete pitch-and-time equivalence.",
        "qualification_receipt_check": {
            "calls_recorded": len(calls), "recorded_passes": len(passed),
            "retained_failed_fixture_calls": len(failed),
            "failed_name": failed[0]["name"],
            "fixture_correction_as_recorded": ledger["fixture_correction"],
            "classification_scope": "Counts and stored process responses are verified; the cause of the earlier failed fixture is the retained ledger explanation, not a rerun by this validator.",
            "process_calls": process_receipts, "artifact_sha256": qualification_hashes,
            "guard_scope": "Process outputs, removals, storage and arrival receipts checked. The ready/guard handshake is not separately persisted; this script does not dynamically test filesystem or network denial.",
        },
        "new_candidate_calls": 0, "new_material_generations": 0,
        "audio_renderings": 0, "scientific_rate_scores_computed": 0,
        "interpretation": "The retained partial inputs are internally consistent. No complete panel, ambiguity certificate or method qualification follows from this validation.",
    }


if __name__ == "__main__":
    result = validate()
    destination = ROOT / "saved-input-validation.json"
    if destination.exists():
        raise FileExistsError("Preserve the existing validation receipt; no overwrite")
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": result["validation_status"], "counts": result["counts"],
                      "runtime_seconds": result["runtime_seconds"],
                      "output": str(destination)}, indent=2))
