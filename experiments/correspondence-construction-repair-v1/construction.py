"""Independent evaluator-side construction guard and verified panel completion.

No matcher, engine, model or runner is imported. Root alone calls build_panel.
The frozen 35 sessions are copied byte-for-byte; only the unsaved fourth novel
family is generated in this new preparation. A failure is terminal, with a new
full witness. The missing original failure evidence is never reconstructed.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT.parent / "correspondence-reference-choice-v1"
ORIGINAL_SOURCE_SHA256 = "9ea4a2e66b628523d441e402f623988cfb7513973279d323e8654219279d7f10"
ROUND_OFF_SECONDS = 1e-9


class ConstructionRejected(ValueError):
    """The fixed material fails the independently declared complete relation."""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def load_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def full_relation(template, window):
    """One pitch shift and positive affine time map across all 12 notes.

    Map template -> window. The first onset and last offset determine scale and
    offset; all 24 endpoints independently have to satisfy the same map. This
    algebra is evaluator code, not a call to or derivative of Candidate G.
    """
    template = np.asarray(template, dtype=np.float64)
    window = np.asarray(window, dtype=np.float64)
    if template.shape != (12, 3) or window.shape != (12, 3):
        raise ValueError("Full construction relation requires two12-event arrays")
    if not np.isfinite(template).all() or not np.isfinite(window).all():
        raise ValueError("Nonfinite construction events")
    for sequence in (template, window):
        if np.any(sequence[:, 1] <= sequence[:, 0]):
            raise ValueError("Nonpositive construction note duration")
        if np.any(sequence[1:, 0] < sequence[:-1, 1] - ROUND_OFF_SECONDS):
            raise ValueError("Overlapping construction events")
        if np.any(sequence[:, 2] != np.rint(sequence[:, 2])):
            raise ValueError("Construction pitches must be exact integers")
    pitch_differences = window[:, 2] - template[:, 2]
    shift = int(pitch_differences[0])
    pitch_only = bool(np.all(pitch_differences == shift))
    scale = float((window[-1, 1] - window[0, 0]) /
                  (template[-1, 1] - template[0, 0]))
    offset = float(window[0, 0] - scale * template[0, 0])
    residuals = window[:, :2] - (scale * template[:, :2] + offset)
    maximum = float(np.max(np.abs(residuals)))
    return {
        "pitch_only_match": pitch_only, "pitch_translation": shift,
        "pitch_differences": pitch_differences.astype(int).tolist(),
        "time_scale": scale, "time_offset": offset,
        "endpoint_residuals_seconds": residuals.tolist(),
        "max_abs_endpoint_residual_seconds": maximum,
        "positive_time_scale": bool(scale > 0),
        "full_equivalent": bool(pitch_only and scale > 0 and maximum <= ROUND_OFF_SECONDS),
    }


def guard_with_witness(source, query, history, cell, path, *, session_id, provenance):
    """Save actual arrays and every window check before any terminal rejection."""
    source = np.asarray(source, dtype=np.float64)
    query = np.asarray(query, dtype=np.float64)
    history = np.asarray(history, dtype=np.float64)
    witness = {
        "schema": "earworm-independent-construction-witness-v1",
        "session_id": session_id, "cell": cell,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "source_events_relative": source.tolist(), "query_events_relative": query.tolist(),
        "history_events_absolute": history.tolist(),
        "candidate_window_start_indices": list(range(len(history) - 11)),
        "roundoff_tolerance_seconds": ROUND_OFF_SECONDS,
        "relation": "window_time=a*template_time+b with a>0 for all12onsets+offsets; every pitch translated by one common integer",
        "original_failed_execution_arrays": "Missing; this witness is new preparation evidence only",
        "checks_complete": False,
    }
    # Even an exception in validation retains the raw actual arrays first.
    write_json(path, witness)
    source_windows = []
    query_windows = []
    for start in witness["candidate_window_start_indices"]:
        window = history[start:start + 12]
        source_windows.append({"window_start_index": start, **full_relation(source, window)})
        query_windows.append({"window_start_index": start, **full_relation(query, window)})
    source_full = [x["window_start_index"] for x in source_windows if x["full_equivalent"]]
    source_pitch = [x["window_start_index"] for x in source_windows if x["pitch_only_match"]]
    query_full = [x["window_start_index"] for x in query_windows if x["full_equivalent"]]
    query_pitch = [x["window_start_index"] for x in query_windows if x["pitch_only_match"]]
    reasons = []
    if source_full != [2]:
        reasons.append("Earlier full-equivalent source occurrences differ from sole expected index2")
    if cell in ("inventory_foil", "near_foil") and query_full:
        reasons.append("Complete foil pitch/time equivalent already occurs in earlier history")
    witness.update(source_windows=source_windows, query_windows=query_windows,
                   source_pitch_only_matches=source_pitch, source_full_matches=source_full,
                   query_pitch_only_matches=query_pitch, query_full_matches=query_full,
                   expected_source_start_index=2, checks_complete=True,
                   accepted=not reasons, rejection_reasons=reasons)
    write_json(path, witness)
    if reasons:
        raise ConstructionRejected("; ".join(reasons))
    # Preserve the historical label field's literal pitch-signature meaning.
    return source_pitch


def _repaired_generator():
    """Verify that the only copied-source edit is the terminal guard replacement."""
    original_path = ORIGINAL / "materials.py"
    assert sha(original_path) == ORIGINAL_SOURCE_SHA256
    original = original_path.read_text()
    first = original.index("    source_occurrences = [j for j in range(len(history) - 11)")
    last = original.index("    events = np.concatenate([history, query +", first)
    permitted = original[:first] + "    source_occurrences = _terminal_guard(source, query, history, cell)\n" + original[last:]
    path = ROOT / "materials_repaired.py"
    if path.read_text() != permitted:
        raise ValueError("Copied generator differs outside the permitted terminal guard block")
    spec = importlib.util.spec_from_file_location("earworm_materials_terminal_guard_repair", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(directory, labels, *, origin):
    files = {name: {"sha256": sha(directory / name), "bytes": (directory / name).stat().st_size}
             for name in ("rows.npz", "exact-events.npz", "evaluatorlabels.json")}
    rows = load_npz(directory / "rows.npz")
    events = load_npz(directory / "exact-events.npz")["events"]
    return {"session_id": labels["session_id"], "path": directory.name,
            "group": labels["group"], "cell": labels["cell"], "stratum": labels["stratum"],
            "files": files, "rows": len(rows["t"]), "events": len(events),
            "decision_seconds": labels["decision_seconds"], "origin": origin}


def build_panel(outputdir):
    """Root-only, one-use construction; never execute candidates on partial data."""
    began = time.monotonic()
    started = datetime.now(timezone.utc).isoformat()
    output = Path(outputdir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Refusing to repeat or replace a started preparation")
    output.mkdir(parents=True, exist_ok=True)
    old_panel = ORIGINAL / "inputs" / "panel"
    old_failure = read_json(old_panel / "construction-failure.json")
    original_manifest = read_json(old_panel / "generation-manifest.json")
    assert len(old_failure["completed_sessions"]) == 35
    assert old_failure["current"] == "novel-20260926-04--unchanged"
    write_json(output / "preparation-provenance.json", {
        "started_utc": started, "new_preparation": True,
        "original_source_sha256": ORIGINAL_SOURCE_SHA256,
        "original_failure_sha256": sha(old_panel / "construction-failure.json"),
        "original_generation_manifest_sha256": sha(old_panel / "generation-manifest.json"),
        "repaired_generator_sha256": sha(ROOT / "materials_repaired.py"),
        "construction_guard_sha256": sha(Path(__file__)),
        "source_publication": "4aac104649fe4d84796386c3b19766aa318a3e31",
        "successor_base": "c09c768b711104010e71184d495d714efe45dad7",
        "original_failed_arrays": "Remain missing; newly generated arrays are not their recovery",
        "reused_sessions": 35, "planned_new_sessions": 5,
        "fixed_new_family": "novel-20260926-04", "fixed_seed": 202609260103,
    })
    completed = []
    witnesses = []
    current = None
    try:
        generator = _repaired_generator()
        # Copy every original session before any new musical construction.
        for old in old_failure["completed_sessions"]:
            current = old["session_id"]
            source_dir = old_panel / old["path"]
            destination = output / old["path"]
            destination.mkdir()
            for name, record in old["files"].items():
                assert sha(source_dir / name) == record["sha256"]
                assert (source_dir / name).stat().st_size == record["bytes"]
                shutil.copyfile(source_dir / name, destination / name)
                assert sha(destination / name) == record["sha256"]
            labels = read_json(destination / "evaluatorlabels.json")
            completed.append(_entry(destination, labels, origin="verified-byte-identical-PR19-reuse"))
        # Reconcile all saved histories against the corrected complete relation.
        for entry in completed:
            current = entry["session_id"]
            directory = output / entry["path"]
            labels = read_json(directory / "evaluatorlabels.json")
            events = load_npz(directory / "exact-events.npz")["events"]
            history = events[events[:, 0] < labels["query_interval"][0]]
            path = output / "construction-witnesses" / (current + ".json")
            guard_with_witness(labels["source_events"], labels["query_events"], history,
                               labels["cell"], path, session_id=current,
                               provenance="Recomputed arithmetic from byte-identical saved PR19 input, not regenerated")
            witnesses.append({"session_id": current, "path": path.relative_to(output).as_posix(), "sha256": sha(path)})
        group, = [g for g in original_manifest["groups"] if g["group"] == "novel-20260926-04"]
        assert group["seed"] == 202609260103
        current = group["group"]
        historical_signatures, old_bach = generator._historical_development()
        source, provenance = generator._source(group, old_bach)  # Exactly one new source construction.
        signature = generator._signature(source[:, 2])
        prior_new_signatures = {tuple(read_json(output / entry["path"] / "evaluatorlabels.json")["source_interval_signature"])
                                for entry in completed}
        if signature in historical_signatures or signature in prior_new_signatures:
            # Retain source before any unchanged nonreuse guard rejection too.
            write_json(output / "new-source-before-rejection.json", {
                "source": source.tolist(), "provenance": provenance, "group": group,
                "recorded_utc": datetime.now(timezone.utc).isoformat(),
                "historical_signature_collision": signature in historical_signatures,
                "new_panel_signature_collision": signature in prior_new_signatures})
            raise ConstructionRejected("Fixed new source fails unchanged nonreuse guard")
        figures = generator._distractors(source, group)  # Exactly one fixed interference construction.
        write_json(output / "new-family-construction.json", {
            "recorded_utc": datetime.now(timezone.utc).isoformat(), "group": group,
            "source": source.tolist(), "source_provenance": provenance,
            "figures": [figure.tolist() for figure in figures],
            "historical_signature_count": len(historical_signatures),
            "nonreuse_checks_passed": True,
            "evidence_status": "New preparation; original failed-session arrays remain missing"})
        for cell in generator.CELLS:
            current = group["group"] + "--" + cell
            witness_path = output / "construction-witnesses" / (current + ".json")
            def terminal(s, q, h, c):
                return guard_with_witness(s, q, h, c, witness_path, session_id=current,
                                          provenance="New fixed-seed construction for explicitly authorized repair preparation")
            generator._terminal_guard = terminal
            rows, exact, labels = generator._session(group, cell, source, provenance, figures)
            witnesses.append({"session_id": current, "path": witness_path.relative_to(output).as_posix(), "sha256": sha(witness_path)})
            directory = output / current
            directory.mkdir()
            np.savez_compressed(directory / "rows.npz", **rows)
            np.savez_compressed(directory / "exact-events.npz", **exact)
            write_json(directory / "evaluatorlabels.json", labels)
            completed.append(_entry(directory, labels, origin="new-once-only-fixed-family-completion"))
        assert len(completed) == 40 and len(witnesses) == 40
        manifest = {
            "schema": "correspondence-reference-input-archive-v1", "status": "complete",
            "construction_branch": "Result A: independent complete-relation construction admissible",
            "schema_contract": "input-manifest.json; sessions[].session_id and path; no id alias",
            "sessions": completed, "total_sessions": 40, "reused_sessions": 35,
            "new_sessions": 5, "construction_witnesses": witnesses,
            "construction_compute_seconds": time.monotonic() - began,
            "candidate_readouts": 0, "audio_renderings": 0,
            "preregistration_status": "Required separately before any candidate execution",
        }
        write_json(output / "input-manifest.json", manifest)
        return manifest
    except Exception as error:
        write_json(output / "construction-failure.json", {
            "status": "Result B: withheld-construction", "current": current,
            "exception": type(error).__name__, "message": str(error),
            "completed_sessions": completed, "completed_witnesses": witnesses,
            "all_witness_paths": [p.relative_to(output).as_posix() for p in sorted((output / "construction-witnesses").glob("*.json"))],
            "construction_compute_seconds": time.monotonic() - began,
            "candidate_readouts": 0, "replacements_attempted": 0,
            "resume_owner": "PM", "resume_condition": "Separate explicit disposition; no automatic repair or retry",
        })
        raise
