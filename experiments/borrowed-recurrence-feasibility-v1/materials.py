"""Evaluator-only frozen material construction; never import into a listener.

``split_manifest()`` reads only the acquisition manifest, never score bytes.
``make_session(group, cell, allow_evaluation=False)`` returns
``(pcm_float32_24kHz, clean_ceiling_arrays, labels_json)`` without writing files.
Evaluation generation requires an explicit flag after preregistration. Labels
describe construction correspondence, not human perceptual identity.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import numpy as np

from midi_reader import read_midi

ROOT = Path(__file__).resolve().parent
SR = 24000
CELLS = ("unchanged", "transpose", "stretch", "foil")
BACH_SPLITS = {"development": (773, 775, 778, 781),
               "evaluation": (774, 776, 779, 782, 784, 785, 786, 787)}
SHIFTS = (-5, -2, 2, 5)
STRETCHES = (0.8, 1.25)
SOURCE_SECONDS = 3.0
INTERFERENCE_SECONDS = 32.0


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def split_manifest():
    """Return all frozen IDs/settings/provenance without opening any MIDI file."""
    raw = (ROOT / "sources/manifest.json").read_bytes()
    source = json.loads(raw)
    midi = {f["bwv"]: f for f in source["files"] if f["path"].endswith(".mid")}
    groups = []
    for split, works in BACH_SPLITS.items():
        for stratum in ("bach", "novel"):
            for i in range(len(works)):
                bwv = works[i] if stratum == "bach" else None
                gid = f"bach-bwv{bwv}" if bwv else f"novel-{split}-{i + 1:02d}"
                seed = (202609220300 + bwv if bwv else
                        (202609220100 if split == "development" else 202609220200) + i)
                group = {"group": gid, "id": gid, "split": split, "stratum": stratum,
                         "seed": seed, "index_within_stratum": i,
                         "transpose_semitones": SHIFTS[i % 4],
                         "stretch_ratio": STRETCHES[i % 2],
                         "source_onset_seconds": 1.13 + 0.17 * (i % 4)}
                if bwv:
                    if midi[bwv]["split"] != split:
                        raise ValueError("Acquisition split disagrees with frozen split")
                    group.update(bwv=bwv, source_provenance=dict(midi[bwv]))
                else:
                    group["source_provenance"] = {
                        "type": "new deterministic diatonic composition",
                        "seed": seed, "rights": "Original project-generated material",
                        "claim": "Newly constructed here; no claim of human unfamiliarity"}
                groups.append(group)
    return {
        "schema": "borrowed-recurrence-materials-v1", "sample_rate": SR,
        "groups": groups, "cells": list(CELLS),
        "source_manifest_sha256": _digest(raw),
        "source_policy": "First nonempty note track; first 12 events; reject overlapping notes and any sustain messages; linearly normalize the complete onset-to-offset span to 3 seconds",
        "novel_policy": "Seeded bounded diatonic random walk with 12 events and varied quarter/eighth-note durations; normalize span to 3 seconds",
        "distractor_policy": "Eight distinct 4-second figures: four same-pitch-histogram near-neighbor reorderings and four newly composed diatonic figures; none has the source's complete ordered interval sequence",
        "foil_policy": "Deterministic full permutation of source pitches with at least six changed positions and at least four changed positions among the last eight; preserve exact event timing, pitch histogram, register, length and timbre",
        "renderer": {"type": "Analytical isolated monophonic score rendering, not natural performance",
                     "harmonics": [1.0, 0.3, 0.15, 0.07], "amplitude": 0.18,
                     "phase": "Every note begins at zero phase",
                     "edge_fade_seconds": 0.008, "velocity": "Fixed; MIDI velocity ignored"},
        "source_seconds": SOURCE_SECONDS, "interference_seconds": INTERFERENCE_SECONDS,
        "trailing_silence_seconds": 0.25, "pad_to_whole_seconds": True,
        "ceiling": "Score pitch at each 0.1-second frame center, 128 absolute MIDI dimensions plus silence; availability only after the containing one-second extraction unit",
        "equivalence": "Only the earlier complete source occurrence is equivalent; relation defined from independently retained ordered pitch and timing construction; not a perceptual judgment",
        "exclusion_policy": "Reject malformed, chordal, pedal-dependent, out-of-range or insufficient-note material without replacement; abort evaluation on such failure",
    }


def _canonical_pitches(pitches):
    pitches = np.asarray(pitches, dtype=np.int64)
    return tuple(np.diff(pitches).tolist())


def _normalized(notes, seconds):
    notes = np.asarray(notes, dtype=np.float64)
    if notes.shape != (12, 3):
        raise ValueError("Exactly twelve onset/offset/pitch events are required")
    if np.any(notes[:, 1] <= notes[:, 0]):
        raise ValueError("Non-positive duration")
    if np.any(notes[1:, 0] < notes[:-1, 1] - 1e-10):
        raise ValueError("Chordal/overlapping notes are excluded, never selected away")
    if np.any((notes[:, 2] < 24) | (notes[:, 2] > 104)):
        raise ValueError("Pitch outside the frozen spectral coverage")
    span = notes[-1, 1] - notes[0, 0]
    result = notes.copy()
    result[:, :2] = (result[:, :2] - notes[0, 0]) * (seconds / span)
    result[-1, 1] = seconds
    return result


def _composed(rng, seconds=SOURCE_SECONDS, tonic=60):
    degrees = np.empty(12, dtype=np.int64)
    degrees[0] = int(rng.integers(0, 5))
    steps = np.array([-3, -2, -1, 1, 2, 3])
    for i in range(1, 12):
        proposed = degrees[i - 1] + int(rng.choice(steps))
        degrees[i] = max(-3, min(10, proposed))
    scale = np.array([0, 2, 4, 5, 7, 9, 11])
    pitches = tonic + 12 * np.floor_divide(degrees, 7) + scale[degrees % 7]
    durations = rng.choice(np.array([1.0, 1.0, 1.0, 2.0, 0.5]), size=12)
    ends = np.cumsum(durations)
    return _normalized(np.column_stack((np.r_[0.0, ends[:-1]], ends, pitches)), seconds)


def source_notes(group, *, allow_evaluation=False):
    """Evaluator-only notes and extraction provenance; explicit evaluation gate."""
    if group["split"] == "evaluation" and not allow_evaluation:
        raise PermissionError("Evaluation source exposure requires preregistration and allow_evaluation=True")
    if group["stratum"] == "novel":
        notes = _composed(np.random.default_rng(group["seed"]), tonic=60 + (group["index_within_stratum"] % 4))
        return notes, dict(group["source_provenance"])
    info = group["source_provenance"]
    path = ROOT / info["path"]
    if _digest(path.read_bytes()) != info["sha256"]:
        raise ValueError("Source MIDI hash differs from the acquisition manifest")
    midi = read_midi(path)
    track_index, track = next((i, t) for i, t in enumerate(midi["tracks"]) if t["notes"])
    if track["sustain_pedal"] or track["overlapping_note_ons"]:
        raise ValueError("Pedal/ambiguous repeated-note overlap is excluded")
    first = track["notes"][:12]
    if len(first) != 12:
        raise ValueError("Fewer than twelve note events")
    notes = _normalized([[n[0], n[1], n[2]] for n in first], SOURCE_SECONDS)
    # Check the following event too: it must not overlap the chosen last event.
    if len(track["notes"]) > 12 and track["notes"][12][0] < first[-1][1] - 1e-10:
        raise ValueError("Excerpt ends inside an overlapping note event")
    provenance = {**info, "midi_track_index": track_index, "midi_track_name": track["name"],
                  "voice": "First nonempty MIDI note track, isolated from other voices",
                  "movement": "Complete named invention/sinfonia; initial 12-event excerpt",
                  "note_indices": list(range(12)),
                  "quarter_span": [first[0][0], first[-1][1]],
                  "original_quarter_events": first,
                  "rendering": "Analytical monophonic rendering of score-derived events"}
    return notes, provenance


def _foil(source, rng):
    original = source[:, 2].astype(np.int64)
    for _ in range(1000):
        reordered = rng.permutation(original)
        if (np.count_nonzero(reordered != original) >= 6
                and np.count_nonzero(reordered[4:] != original[4:]) >= 4
                and _canonical_pitches(reordered) != _canonical_pitches(original)):
            result = source.copy()
            result[:, 2] = reordered
            return result
    raise ValueError("Cannot construct the preregistered same-histogram foil")


def _distractors(source, rng, excluded=()):
    """Eight distinct figures, no source-equivalent complete pitch sequence."""
    original = source[:, 2].astype(np.int64)
    seen = {_canonical_pitches(original)} | set(excluded)
    figures = []
    for i in range(8):
        for _ in range(1000):
            if i < 4:
                candidate = source.copy()
                pitches = original.copy()
                # Related distractors alter two to four positions, preserving
                # the source's pitch inventory, register, and rhythmic pattern.
                positions = rng.choice(12, size=2 + i % 3, replace=False)
                pitches[positions] = np.roll(pitches[positions], 1)
                candidate[:, 2] = pitches
                candidate = _normalized(candidate, 4.0)
            else:
                candidate = _composed(rng, seconds=4.0, tonic=int(np.median(original)) - 4)
            signature = _canonical_pitches(candidate[:, 2])
            if signature not in seen:
                seen.add(signature)
                figures.append(candidate)
                break
        else:
            raise ValueError("Could not construct eight distinct non-equivalent distractors")
    return figures


def _render(events, length):
    pcm = np.zeros(length, dtype=np.float64)
    for start, end, pitch in events:
        a, b = int(round(start * SR)), int(round(end * SR))
        if b <= a or a < 0 or b > length:
            raise ValueError("Invalid sample support")
        t = np.arange(b - a, dtype=np.float64) / SR
        frequency = 440.0 * 2.0 ** ((pitch - 69.0) / 12.0)
        signal = np.zeros(len(t), dtype=np.float64)
        for harmonic, amplitude in enumerate((1.0, 0.3, 0.15, 0.07), start=1):
            if harmonic * frequency < SR / 2:
                signal += amplitude * np.sin(2 * np.pi * harmonic * frequency * t)
        fade = min(int(0.008 * SR), len(t) // 2)
        if fade:
            ramp = np.sin(np.linspace(0, np.pi / 2, fade, endpoint=True)) ** 2
            signal[:fade] *= ramp
            signal[-fade:] *= ramp[::-1]
        pcm[a:b] += 0.18 * signal
    if np.max(np.abs(pcm)) >= 1.0:
        raise ValueError("Clipping")
    return pcm.astype(np.float32)


def make_session(group, cell, *, allow_evaluation=False):
    """Return PCM, isolated score ceiling and evaluator-only labels; no saves.

    ``group`` may be a manifest group dict or its string ID. The sole audio
    listener input is PCM delivered in consecutive one-second units. Labels,
    ceiling arrays and returned event metadata must remain evaluator-side.
    """
    known = {g["group"]: g for g in split_manifest()["groups"]}
    if isinstance(group, str):
        group = known[group]
    elif group != known.get(group.get("group")):
        raise ValueError("Group configuration differs from the frozen manifest")
    if cell not in CELLS:
        raise ValueError(f"Unknown cell: {cell}")
    source, provenance = source_notes(group, allow_evaluation=allow_evaluation)
    rng = np.random.default_rng(group["seed"] + 1000000)
    foil = _foil(source, rng)
    distractors = _distractors(source, rng, excluded=(_canonical_pitches(foil[:, 2]),))
    shift = group["transpose_semitones"] if cell == "transpose" else 0
    stretch = group["stretch_ratio"] if cell == "stretch" else 1.0
    query = foil.copy() if cell == "foil" else source.copy()
    query[:, :2] *= stretch
    query[:, 2] += shift
    if np.any((query[:, 2] < 24) | (query[:, 2] > 104)):
        raise ValueError("Transformed phrase outside frozen spectral coverage")

    onset = group["source_onset_seconds"]
    source_end = onset + SOURCE_SECONDS
    query_start = source_end + INTERFERENCE_SECONDS
    query_end = query_start + SOURCE_SECONDS * stretch
    decision_seconds = int(math.ceil(query_end + 0.25))
    # A short independent two-note lead-in embeds the source in the stream.
    prelude = np.array([[0.0, onset * 0.48, source[0, 2] - 7],
                        [onset * 0.48, onset, source[0, 2] - 2]], dtype=np.float64)
    events = [prelude, source + np.array([onset, onset, 0.0])]
    distractor_labels = []
    for i, notes in enumerate(distractors):
        start = source_end + 4.0 * i
        events.append(notes + np.array([start, start, 0.0]))
        distractor_labels.append({"interval": [start, start + 4.0],
                                  "kind": "near-neighbor" if i < 4 else "new diatonic figure",
                                  "relative_events": notes.tolist(),
                                  "interval_signature": list(_canonical_pitches(notes[:, 2]))})
    events.append(query + np.array([query_start, query_start, 0.0]))
    events = np.concatenate(events)
    if np.any(events[1:, 0] < events[:-1, 1] - 1e-9):
        raise ValueError("Renderer event stream is not monophonic")
    # Validate every earlier 12-event window, including figure boundaries.
    # A construction failure stops the session; no evaluation replacement.
    earlier = events[:-12]
    source_signature = _canonical_pitches(source[:, 2])
    occurrences = [i for i in range(len(earlier) - 11)
                   if _canonical_pitches(earlier[i:i + 12, 2]) == source_signature]
    if occurrences != [2]:
        raise ValueError("Earlier stream contains an unintended complete source-equivalent occurrence")
    if cell == "foil":
        foil_signature = _canonical_pitches(foil[:, 2])
        if any(_canonical_pitches(earlier[i:i + 12, 2]) == foil_signature
               for i in range(len(earlier) - 11)):
            raise ValueError("The unrelated foil already occurs in the earlier stream")
    pcm = _render(events, decision_seconds * SR)

    times = np.arange(decision_seconds * 10, dtype=np.float64) * 0.1 + 0.05
    clean = np.zeros((len(times), 129), dtype=np.float32)
    clean[:, 128] = 1.0
    rms = np.zeros(len(times), dtype=np.float64)
    for start, end, pitch in events:
        use = (times >= start) & (times < end)
        clean[use, 128] = 0.0
        clean[use, int(pitch)] = 1.0
        rms[use] = 0.1  # Score-derived occupancy cue, explicitly not measured audio energy.
    ceiling = {"t": times, "rms": rms, "clean": clean,
               "unit": np.repeat(np.arange(decision_seconds, dtype=np.int64), 10)}
    labels = {
        "schema": "borrowed-recurrence-session-labels-v1", "group": group["group"],
        "split": group["split"], "stratum": group["stratum"], "cell": cell,
        "session_id": f"{group['group']}--{cell}", "seed": group["seed"],
        "source_interval": [onset, source_end], "query_interval": [query_start, query_end],
        "source_onset": onset, "source_offset": source_end,
        "query_onset": query_start, "query_offset": query_end,
        "source_equivalent_occurrences": [[onset, source_end]],
        "equivalent_occurrences": [{"id": "source", "onset": onset, "offset": source_end}],
        "positive": cell != "foil", "truth_shift": shift if cell != "foil" else None,
        "truth_stretch": stretch if cell != "foil" else None,
        "shift": shift if cell != "foil" else None,
        "stretch": stretch if cell != "foil" else None,
        "decision_seconds": decision_seconds, "decision_sample": len(pcm),
        "query_final_required_sample": int(math.ceil(query_end * SR)),
        "interference_seconds": INTERFERENCE_SECONDS, "distinct_distractor_figures": 8,
        "source_events": source.tolist(), "query_events": query.tolist(),
        "distractors": distractor_labels, "all_rendered_events": events.tolist(),
        "source_provenance": provenance, "pcm_sha256": _digest(pcm.tobytes()),
        "pcm_bytes": pcm.nbytes, "sample_rate": SR,
        "identity_definition": "Construction correspondence to the one earlier complete source; no perceptual identity assertion",
        "ceiling_rms_semantics": "Score occupancy at frame centers: 0.1 while a note is active, 0 otherwise; not acoustic RMS",
    }
    return pcm, ceiling, labels


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="store_true", help="Print split manifest only; opens no scores")
    args = parser.parse_args()
    if args.manifest:
        print(json.dumps(split_manifest(), indent=2))
    else:
        parser.error("Use --manifest; stream generation is exposed only as the guarded Python API")
