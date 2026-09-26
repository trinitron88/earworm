"""Evaluator-only fixed development material; no candidate imports or execution.

``make_manifest()`` records inputs/settings without parsing musical content.
``build_all(outputdir)`` constructs and archives the one fixed 40-session panel.
No audio is rendered. Predictor inputs are only rows.npz or, for the separately
labeled richer diagnostic, exact-events.npz. Labels and this module stay outside
predictors. Every construction failure is terminal; there is no replacement.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT.parent / "borrowed-recurrence-feasibility-v1"
WORKS = (773, 775, 778, 781)
CELLS = ("unchanged", "transpose", "stretch", "inventory_foil", "near_foil")
SHIFTS = (-5, -2, 2, 5)
SCALES = (0.8, 1.25, 0.8, 1.25)
SOURCE_SECONDS = 3.0
INTERFERENCE_SECONDS = 32.0
NOTE_INDICES = tuple(range(24, 36))
NEW_SEED_BASE = 202609260100


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _json_write(path, value):
    path.write_bytes(_json_bytes(value))


def _history_paths():
    ids = [f"bach-bwv{bwv}" for bwv in WORKS]
    ids += [f"novel-development-{i + 1:02d}" for i in range(4)]
    return [HISTORY / "results" / "development" / f"{gid}-unchanged" / "labels.json"
            for gid in ids]


def make_manifest():
    """Hashes original bytes/settings only; never parses score events or labels."""
    source_raw = (HISTORY / "sources" / "manifest.json").read_bytes()
    acquired = json.loads(source_raw)
    midi = {f["bwv"]: f for f in acquired["files"]
            if f["path"].endswith(".mid") and f["bwv"] in WORKS}
    groups = []
    for stratum in ("bach", "novel"):
        for i in range(4):
            bwv = WORKS[i] if stratum == "bach" else None
            group = {
                "group": f"bach-bwv{bwv}-notes24-35" if bwv else f"novel-20260926-{i + 1:02d}",
                "split": "development", "stratum": stratum,
                "index_within_stratum": i,
                "seed": NEW_SEED_BASE + (1000 + bwv if bwv else i),
                "source_onset_seconds": 1.13 + 0.17 * i,
                "transpose_semitones": SHIFTS[i], "stretch_ratio": SCALES[i],
            }
            if bwv:
                info = midi[bwv]
                if info["split"] != "development":
                    raise ValueError("Requested Bach input is not historical development material")
                raw = (HISTORY / info["path"]).read_bytes()
                if _sha(raw) != info["sha256"]:
                    raise ValueError(f"Acquired BWV{bwv} source hash mismatch")
                group.update(bwv=bwv, note_indices=list(NOTE_INDICES), source_provenance=info)
            else:
                group["source_provenance"] = {
                    "type": "new deterministic diatonic motif",
                    "seed": group["seed"], "rights": "Original project-generated material",
                    "claim": "New construction, not a human or pretrained familiarity judgment",
                }
            groups.append(group)
    history_inputs = [{"path": p.relative_to(ROOT.parent.parent).as_posix(),
                       "sha256": _sha(p.read_bytes())} for p in _history_paths()]
    return {
        "schema": "correspondence-reference-material-manifest-v1",
        "groups": groups, "cells": list(CELLS), "sessions": 40,
        "source_seconds": SOURCE_SECONDS, "interference_seconds": INTERFERENCE_SECONDS,
        "query_rule": "Last 20 rows ending at the final occupied 100-ms center",
        "row_centers_seconds": "0.05 + 0.1*k", "completed_unit_availability": "floor(t)+1",
        "occupancy_semantics": "rms is a score-derived 0/1 occupancy cue, not acoustic RMS",
        "source_manifest_sha256": _sha(source_raw),
        "midi_reader_sha256": _sha((HISTORY / "midi_reader.py").read_bytes()),
        "historical_development_signature_inputs": history_inputs,
        "historical_access_scope": "Only eight PR18 development unchanged-session labels; no evaluation files",
        "source_policy": "Same first nonempty note track as historical development; note indices24..35; normalize onset-to-offset span to three seconds; verify no event-range overlap with prior indices0..11",
        "novel_policy": "One PCG64 draw per fixed new seed; twelve-event diatonic walk and durations; reject interval-signature collision without resampling",
        "novel_nonreuse_scope": "Compare every 12-event window in eight PR18 development unchanged histories and all new source signatures; historical evaluation is excluded",
        "foil_policy": "Sort pitch positions stably, then cyclically shift sorted pitches by the largest pitch multiplicity; restore original positions; same exact pitch inventory and event timing",
        "near_foil_policy": "Increase pitch by one semitone in the last source event containing a center in the fixed observed query; require at least one changed observed pitch row",
        "interference_policy": "Eight four-second figures: first four fixed cyclic source-pitch shifts1..4 with source timing scaled4/3; last four one-shot new diatonic motifs from seed+2000000; reject complete-signature collisions without replacements",
        "construction_failure_policy": "Abort and retain completed artifacts plus construction-failure.json; never replace a family, seed, excerpt, foil or distractor",
        "prediction_input_policy": "Rows NPZ contains no IDs, source labels, boundaries or exact notes; richer exact-events NPZ contains only ordered note triples and end-completion availability",
        "identity_claim": "Stipulated construction correspondence, not human perceptual identity",
        "numpy_version": np.__version__,
    }


def _signature(pitches):
    return tuple(np.diff(np.asarray(pitches, dtype=np.int64)).tolist())


def _normalize(events, seconds):
    events = np.asarray(events, dtype=np.float64)
    if events.shape != (12, 3) or not np.isfinite(events).all():
        raise ValueError("Expected twelve finite [onset,offset,pitch] events")
    if np.any(events[:, 1] <= events[:, 0]):
        raise ValueError("Nonpositive note duration")
    if np.any(events[1:, 0] < events[:-1, 1] - 1e-10):
        raise ValueError("Polyphonic or overlapping excerpt")
    if np.any((events[:, 2] < 24) | (events[:, 2] > 104)):
        raise ValueError("Pitch outside fixed range")
    if np.any(events[:, 2] != np.rint(events[:, 2])):
        raise ValueError("Noninteger MIDI pitch")
    result = events.copy()
    result[:, :2] = (result[:, :2] - events[0, 0]) * (seconds / (events[-1, 1] - events[0, 0]))
    result[-1, 1] = seconds
    return result


def _compose(rng, seconds, tonic):
    degrees = np.empty(12, dtype=np.int64)
    degrees[0] = int(rng.integers(0, 5))
    for j in range(1, 12):
        step = int(rng.choice(np.array([-3, -2, -1, 1, 2, 3])))
        degrees[j] = max(-3, min(10, degrees[j - 1] + step))
    scale = np.array([0, 2, 4, 5, 7, 9, 11])
    pitches = tonic + 12 * np.floor_divide(degrees, 7) + scale[degrees % 7]
    durations = rng.choice(np.array([1.0, 1.0, 1.0, 2.0, 0.5]), size=12)
    ends = np.cumsum(durations)
    return _normalize(np.column_stack((np.r_[0.0, ends[:-1]], ends, pitches)), seconds)


def _reader():
    path = HISTORY / "midi_reader.py"
    spec = importlib.util.spec_from_file_location("earworm_frozen_midi_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_midi


def _historical_development():
    signatures = set()
    bach_provenance = {}
    for path in _history_paths():
        label = json.loads(path.read_bytes())
        if label["split"] != "development" or label["cell"] != "unchanged":
            raise ValueError("Historical material access boundary violated")
        events = np.asarray(label["all_rendered_events"], dtype=np.float64)
        for j in range(len(events) - 11):
            signatures.add(_signature(events[j:j + 12, 2]))
        if label["stratum"] == "bach":
            bach_provenance[label["source_provenance"]["bwv"]] = label["source_provenance"]
    return signatures, bach_provenance


def _source(group, old_bach):
    if group["stratum"] == "novel":
        return _compose(np.random.default_rng(group["seed"]), 3.0,
                        60 + group["index_within_stratum"]), dict(group["source_provenance"])
    info = group["source_provenance"]
    path = HISTORY / info["path"]
    if _sha(path.read_bytes()) != info["sha256"]:
        raise ValueError("Source bytes changed after manifest creation")
    midi = _reader()(path)
    index, track = next((i, t) for i, t in enumerate(midi["tracks"]) if t["notes"])
    prior = old_bach[group["bwv"]]
    if prior["midi_track_index"] != index or prior["sha256"] != info["sha256"]:
        raise ValueError("Bach track/provenance differs from original development")
    if set(prior["note_indices"]) & set(NOTE_INDICES):
        raise ValueError("New Bach range overlaps historical source excerpt")
    if prior["note_indices"] != list(range(12)):
        raise ValueError("Unexpected earlier development note range")
    if track["sustain_pedal"] or track["overlapping_note_ons"]:
        raise ValueError("Pedal or ambiguous note overlap in isolated track")
    selected = track["notes"][24:36]
    if len(selected) != 12:
        raise ValueError("Required indices24..35 unavailable")
    if track["notes"][23][1] > selected[0][0] + 1e-10:
        raise ValueError("Excerpt begins inside an overlapping event")
    if len(track["notes"]) > 36 and track["notes"][36][0] < selected[-1][1] - 1e-10:
        raise ValueError("Excerpt ends inside an overlapping event")
    notes = _normalize([n[:3] for n in selected], 3.0)
    provenance = {**info, "midi_track_index": index, "midi_track_name": track["name"],
                  "note_indices": list(NOTE_INDICES), "previous_note_indices": prior["note_indices"],
                  "quarter_span": [selected[0][0], selected[-1][1]],
                  "original_quarter_events": selected,
                  "voice": "Same first nonempty note track; isolated score representation",
                  "historical_range_overlap": False,
                  "rendering": "None; exact events and sampled clean occupancy only"}
    return notes, provenance


def _inventory_foil(source):
    original = source[:, 2].astype(np.int64)
    order = np.argsort(original, kind="stable")
    multiplicity = int(np.unique(original, return_counts=True)[1].max())
    reordered = np.empty_like(original)
    reordered[order] = np.roll(original[order], multiplicity)
    result = source.copy()
    result[:, 2] = reordered
    if _signature(reordered) == _signature(original):
        raise ValueError("Fixed inventory foil failed to change complete interval signature")
    return result


def _distractors(source, group):
    figures = []
    seen = {_signature(source[:, 2])}
    for shift in (1, 2, 3, 4):
        notes = source.copy()
        notes[:, 2] = np.roll(notes[:, 2], shift)
        notes = _normalize(notes, 4.0)
        signature = _signature(notes[:, 2])
        if signature in seen:
            raise ValueError("Fixed cyclic interference figure has duplicate/source signature")
        seen.add(signature)
        figures.append(notes)
    rng = np.random.default_rng(group["seed"] + 2000000)
    for _ in range(4):
        notes = _compose(rng, 4.0, int(np.median(source[:, 2])) - 4)
        signature = _signature(notes[:, 2])
        if signature in seen:
            raise ValueError("One-shot new interference figure has duplicate/source signature")
        seen.add(signature)
        figures.append(notes)
    return figures


def _sample(events, decision_seconds):
    t = np.arange(decision_seconds * 10, dtype=np.float64) * 0.1 + 0.05
    rows = np.zeros((len(t), 129), dtype=np.float32)
    rows[:, 128] = 1.0
    occupied = np.zeros(len(t), dtype=np.float64)
    for start, end, pitch in events:
        use = (t >= start) & (t < end)
        if np.any(occupied[use]):
            raise ValueError("Multiple simultaneous pitches at an observed sample")
        rows[use, 128] = 0.0
        rows[use, int(pitch)] = 1.0
        occupied[use] = 1.0
    units = np.floor(t).astype(np.int64)
    return {"t": t, "unit": units, "rms": occupied, "clean": rows,
            "available_at": (units + 1).astype(np.float64)}


def _near_foil(source, query_start):
    final_end = query_start + 3.0
    centers = np.arange(int(math.ceil(final_end + 0.25)) * 10) * 0.1 + 0.05
    active = np.zeros(len(centers), dtype=bool)
    for start, end, _ in source:
        active |= (centers >= query_start + start) & (centers < query_start + end)
    final = np.flatnonzero(active)[-1]
    support = centers[max(0, final - 19):final + 1]
    eligible = [j for j, (start, end, _) in enumerate(source)
                if np.any((support >= query_start + start) & (support < query_start + end))]
    if not eligible:
        raise ValueError("No observed event supports fixed near-foil edit")
    edit = eligible[-1]
    result = source.copy()
    result[edit, 2] += 1
    if result[edit, 2] > 104:
        raise ValueError("Fixed +1 near-foil edit leaves pitch range")
    return result, edit


def _session(group, cell, source, provenance, figures):
    onset = group["source_onset_seconds"]
    source_end = onset + 3.0
    query_start = source_end + 32.0
    shift = group["transpose_semitones"] if cell == "transpose" else 0
    scale = group["stretch_ratio"] if cell == "stretch" else 1.0
    query = source.copy()
    near_edit = None
    if cell == "inventory_foil":
        query = _inventory_foil(source)
    elif cell == "near_foil":
        query, near_edit = _near_foil(source, query_start)
    query[:, :2] *= scale
    query[:, 2] += shift
    if np.any((query[:, 2] < 24) | (query[:, 2] > 104)):
        raise ValueError("Transformed query outside fixed pitch range")
    query_end = query_start + 3.0 * scale
    decision = int(math.ceil(query_end + 0.25))
    prelude = np.array([[0.0, onset * 0.48, source[0, 2] - 7],
                        [onset * 0.48, onset, source[0, 2] - 2]], dtype=np.float64)
    parts = [prelude, source + [onset, onset, 0.0]]
    for i, notes in enumerate(figures):
        start = source_end + 4.0 * i
        parts.append(notes + [start, start, 0.0])
    history = np.concatenate(parts)
    source_occurrences = _terminal_guard(source, query, history, cell)
    events = np.concatenate([history, query + [query_start, query_start, 0.0]])
    if np.any(events[1:, 0] < events[:-1, 1] - 1e-9):
        raise ValueError("Overlapping session events")
    rows = _sample(events, decision)
    final = np.flatnonzero(rows["rms"] > 1e-4)[-1]
    qids = np.arange(final - 19, final + 1, dtype=np.int64)
    observed = rows["t"][qids]
    changed_centers = []
    if cell in ("inventory_foil", "near_foil"):
        original = _sample(np.concatenate([history, source + [query_start, query_start, 0.0]]), decision)
        changed = np.argmax(rows["clean"][qids], axis=1) != np.argmax(original["clean"][qids], axis=1)
        changed_centers = observed[changed].tolist()
        if not changed_centers:
            raise ValueError("Fixed foil has no decisive difference in observed query centers")
    positive = cell in ("unchanged", "transpose", "stretch")
    labels = {
        "schema": "correspondence-reference-evaluator-labels-v1", "group": group["group"],
        "session_id": group["group"] + "--" + cell, "split": "development",
        "stratum": group["stratum"], "cell": cell, "seed": group["seed"],
        "positive": positive, "truth_shift": shift if positive else None,
        "truth_stretch": scale if positive else None,
        "source_interval": [onset, source_end], "query_interval": [query_start, query_end],
        "observed_query_centers": observed.tolist(), "observed_query_row_indices": qids.tolist(),
        "observed_query_support": [float(observed[0] - 0.05), float(observed[-1] + 0.05)],
        "decision_seconds": decision, "source_dependent_units": list(range(int(math.floor(onset)), int(math.ceil(source_end)))),
        "source_events": source.tolist(), "query_events": query.tolist(),
        "source_provenance": provenance,
        "source_interval_signature": list(_signature(source[:, 2])),
        "query_interval_signature": list(_signature(query[:, 2])),
        "earlier_complete_source_signature_occurrences": source_occurrences,
        "interference_intervals": [[source_end + 4.0 * i, source_end + 4.0 * (i + 1)] for i in range(8)],
        "near_foil_changed_event_index": near_edit, "decisive_observed_difference_centers": changed_centers,
        "inventory_preserved": bool(np.array_equal(np.sort(source[:, 2]), np.sort(query[:, 2]))) if cell == "inventory_foil" else None,
        "identity_definition": "Only the earlier stipulated complete source occurrence; partial collisions remain outcomes, not exclusions; no perceptual claim",
    }
    exact = {"events": events, "available_at": np.ceil(events[:, 1]).astype(np.float64)}
    return rows, exact, labels


def build_all(outputdir):
    """Archive once; refuse nonempty output, preserve partial failure evidence.

    Root calls this only for the preregistered preparation workflow. Generation
    is not candidate exposure. The returned manifest records every saved input
    hash; callers must not supply evaluator labels to either candidate.
    """
    started = time.monotonic()
    output = Path(outputdir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Refusing to regenerate a nonempty material archive")
    output.mkdir(parents=True, exist_ok=True)
    manifest = make_manifest()
    _json_write(output / "generation-manifest.json", manifest)
    completed = []
    current = None
    try:
        historical, old_bach = _historical_development()
        new_signatures = set()
        sources = []
        for group in manifest["groups"]:
            current = group["group"]
            source, provenance = _source(group, old_bach)
            signature = _signature(source[:, 2])
            if signature in new_signatures:
                raise ValueError("Two new families share the same complete interval signature")
            if group["stratum"] == "novel" and signature in historical:
                raise ValueError("New novel motif reuses a historical development signature")
            new_signatures.add(signature)
            sources.append((group, source, provenance, _distractors(source, group)))
        for group, source, provenance, figures in sources:
            for cell in CELLS:
                current = group["group"] + "--" + cell
                rows, exact, labels = _session(group, cell, source, provenance, figures)
                session = output / current
                session.mkdir()
                np.savez_compressed(session / "rows.npz", **rows)
                np.savez_compressed(session / "exact-events.npz", **exact)
                _json_write(session / "evaluatorlabels.json", labels)
                files = {name: {"sha256": _sha((session / name).read_bytes()), "bytes": (session / name).stat().st_size}
                         for name in ("rows.npz", "exact-events.npz", "evaluatorlabels.json")}
                completed.append({"session_id": current, "group": group["group"], "cell": cell,
                                  "stratum": group["stratum"], "path": current, "files": files,
                                  "rows": len(rows["t"]), "events": len(exact["events"]),
                                  "decision_seconds": labels["decision_seconds"]})
        result = {"schema": "correspondence-reference-input-archive-v1", "status": "complete",
                  "generation_manifest_sha256": _sha((output / "generation-manifest.json").read_bytes()),
                  "sessions": completed, "total_sessions": len(completed),
                  "construction_compute_seconds": time.monotonic() - started,
                  "historical_signature_count": len(historical),
                  "historical_evaluation_files_opened": 0,
                  "candidate_readouts": 0, "audio_renderings": 0}
        _json_write(output / "input-manifest.json", result)
        return result
    except Exception as error:
        _json_write(output / "construction-failure.json", {
            "status": "invalid-construction", "current": current,
            "exception": type(error).__name__, "message": str(error),
            "completed_sessions": completed, "construction_compute_seconds": time.monotonic() - started,
            "replacements_attempted": 0, "candidate_readouts": 0,
        })
        raise
