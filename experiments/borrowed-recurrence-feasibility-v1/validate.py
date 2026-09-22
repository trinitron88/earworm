"""Independent saved-artifact validation; never reruns a predictor or encoder.

Only completed development/evaluation archives are read. Spectral evidence is
reconstructed with standalone NumPy code, not features.py or runner.py. Access
checks combine the audited child/API boundary with its saved observable state
and context consequences; this is not an adversarial OS-sandbox proof.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

SR = 24000
CATEGORIES = ("software", "provenance", "access", "evidence", "eviction", "preservation")
CELLS = ("unchanged", "transpose", "stretch", "foil")
CONDITIONS = ("full", "recent", "removed")


def _read(path):
    return json.loads(path.read_text())


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _near(a, b, tolerance=1e-8):
    return bool(np.allclose(a, b, rtol=0, atol=tolerance))


def _spectral_reconstruction(pcm, state):
    """Independent whole-session vector implementation, with no feature imports."""
    frames = pcm.astype(np.float64).reshape(-1, 2400)
    window = .5 - .5 * np.cos(2 * np.pi * np.arange(2400) / 2399)
    transformed = np.fft.rfft(frames * window[None, :], n=4096, axis=1)
    density = np.square(np.abs(transformed)) / (4096 * np.sum(np.square(window)))
    density[:, 1:2048] *= 2
    frequency = np.arange(1, 2049, dtype=np.float64) * SR / 4096
    nearest = np.floor(69 + 12 * np.log2(frequency / 440) + .5).astype(np.int64)
    bands = np.stack([np.sum(density[:, 1:][:, nearest == midi], axis=1)
                      for midi in range(24, 105)], axis=1)
    energy = np.sqrt(np.sum(np.square(frames), axis=1) / 2400)
    absolute = np.abs(bands - state["power"])
    relative = absolute / np.maximum(np.abs(bands), 1e-20)
    energy_relative = np.abs(energy - state["rms"]) / np.maximum(np.abs(energy), 1e-20)
    chroma = np.stack([np.sum(bands[:, np.arange(24, 105) % 12 == k], axis=1)
                       for k in range(12)], axis=1)
    norm = np.sum(chroma, axis=1, keepdims=True)
    chroma = np.divide(chroma, norm, out=np.zeros_like(chroma), where=norm > 0)
    quantized = sum((chroma >= threshold).astype(np.int64)
                    for threshold in (.05, .1, .2, .4))
    return {"power_max_relative_error": float(np.max(relative)),
            "power_max_absolute_error": float(np.max(absolute)),
            "rms_max_relative_error": float(np.max(energy_relative)),
            "chroma_quantization_exact": bool(np.array_equal(quantized, state["chroma"])),
            "pass": bool(np.max(relative) <= 1e-6 and np.max(energy_relative) <= 1e-6
                         and np.array_equal(quantized, state["chroma"]))}


def validate(splitdir):
    """Return checks plus detailed evidence, suitable for analyze.analyze().

    This requires a completed split: development has 32 sessions/8 families;
    evaluation has 64 sessions/16 families. Behavioral misses, false accepts,
    and transform errors are left to the frozen analyzer. An ablation reporting
    the removed source location is a control/metric integrity failure.
    """
    started = time.perf_counter()
    out = Path(splitdir).resolve()
    root = out.parent.parent
    split = out.name
    issues = {key: [] for key in CATEGORIES}
    details = []
    source_hashes = {}
    validated_routes = set()
    behavioral_warnings = []

    def check(category, truth, message):
        if not bool(truth):
            issues[category].append(message)
        return bool(truth)

    if split not in ("development", "evaluation"):
        check("software", False, "Split directory must be named development or evaluation")
        expected_groups = 0
    else:
        expected_groups = 8 if split == "development" else 16
    expected_sessions = expected_groups * 4
    try:
        manifest = _read(root / "split.json")
        groups = [g for g in manifest["groups"] if g["split"] == split]
        check("software", len(groups) == expected_groups, "Wrong manifest family count")
        for stratum in ("bach", "novel"):
            check("software", sum(g["stratum"] == stratum for g in groups) * 2 == expected_groups,
                  f"Wrong {stratum} family count")
        bach = {part: {g["bwv"] for g in manifest["groups"]
                       if g["split"] == part and g["stratum"] == "bach"}
                for part in ("development", "evaluation")}
        check("provenance", not bach["development"].intersection(bach["evaluation"]),
              "Bach piece crosses splits")
        source_manifest = root / "sources/manifest.json"
        check("provenance", _sha(source_manifest) == manifest["source_manifest_sha256"],
              "Source manifest differs from split hash")
        for group in groups:
            if group["stratum"] == "bach":
                provenance = group["source_provenance"]
                source_path = root / provenance["path"]
                source_hashes[provenance["path"]] = _sha(source_path)
                check("provenance", source_hashes[provenance["path"]] == provenance["sha256"]
                      and source_path.stat().st_size == provenance["bytes"],
                      f"Source bytes differ for {group['id']}")
                check("provenance", "Public Domain" in provenance["rights_assertion"]
                      and all(provenance.get(k) for k in ("url", "rights_page", "rights_terms_url", "retrieved_utc")),
                      f"Incomplete source rights/provenance for {group['id']}")
                page = root / "provenance" / f"mutopia-{provenance['mutopia_id']}.html"
                check("provenance", page.is_file() and "Public Domain" in page.read_text(),
                      f"Saved edition rights evidence missing for {group['id']}")
        expected_keys = {g["id"] + "-" + cell for g in groups for cell in CELLS}
        completed = _read(out / "completed.json")
        check("software", len(completed) == expected_sessions and set(completed) == expected_keys,
              "Completed session list is incomplete, duplicated, or has extra sessions")
        run = _read(out / "run.json")
        check("software", run["split"] == split and run["completed_sessions"] == expected_sessions,
              "Run completion record disagrees with complete split")
        top_records = _read(out / "records.json")
        top_summaries = _read(out / "summaries.json")
        check("software", len(top_summaries) == expected_sessions, "Wrong aggregate summary count")
        if split == "development":
            routes = ("standard", "mert6", "mert12", "ceiling")
        else:
            selection = _read(root / "selection.json")
            routes = ("standard", selection["selected_mert"], "ceiling")
            check("software", selection["selected_mert"] in ("mert6", "mert12"), "Undeclared MERT candidate")
            freeze = _read(root / "freeze.json")
            receipt = _read(root / "preregistration_receipt.json")
            check("provenance", receipt.get("posted") is True and freeze.get("evaluation_exposed") is False,
                  "Missing preregistration or prior-unexposed freeze")
            for name, digest in freeze["hashes"].items():
                check("provenance", _sha(root / name) == digest, f"Frozen artifact changed: {name}")
        validated_routes.update(routes)
        check("software", len(top_records) == expected_sessions * len(routes) * 3,
              "Wrong aggregate prediction count")
        # Audited implementation boundary, recorded with code hashes below.
        listener_text = (root / "listener.py").read_text()
        runner_text = (root / "runner.py").read_text()
        for filename in ("listener.py", "features.py", "matching.py"):
            tree = ast.parse((root / filename).read_text())
            imports = {node.module.split(".")[0] for node in ast.walk(tree)
                       if isinstance(node, ast.ImportFrom) and node.module}
            imports.update(alias.name.split(".")[0] for node in ast.walk(tree)
                           if isinstance(node, ast.Import) for alias in node.names)
            check("access", not imports.intersection({"materials", "midi_reader"}),
                  f"Evaluator/score importer enters audio code: {filename}")
        check("access", all(s in listener_text for s in
              ("records.clear();ring.clear();del state", "builtins.open=denied", "socket.socket=denied",
               "assert cmd['route']!='ceiling'", "def array_only():")),
              "Audited state clearing/guard/score-child boundary differs")
        check("access", "scorechild=Child(out,True)" in runner_text and
              "(scorechild if route=='ceiling' else child)" in runner_text,
              "Score-only and audio child dispatch are not isolated")
        runtime = _read(out / "runtime.json")["metadata"]
        check("access", runtime["trainable_parameters"] == 0 and not runtime["missing_keys"]
              and not runtime["unexpected_keys"] and runtime["external_downloads"] is False,
              "Encoder frozen/offline/strict-load evidence failed")
        gathered_records, gathered_summaries = [], []
        for key in sorted(expected_keys):
            session_started = time.perf_counter()
            directory = out / key
            try:
                pcm = _arrays(directory / "audio.npz")["pcm"]
                state = _arrays(directory / "measurements.npz")
                ceiling = _arrays(directory / "ceiling.npz")
                labels = _read(directory / "labels.json")
                arrivals = _read(directory / "arrival-log.json")
                summary = _read(directory / "summary.json")
                records = _read(directory / "records.json")
                sequence = [json.loads(line) for line in
                            (directory / "response-before-labels.jsonl").read_text().splitlines()]
                gathered_records.extend(records)
                gathered_summaries.append(summary)
                total = len(pcm) // SR
                frames = total * 10
                check("software", pcm.ndim == 1 and pcm.dtype == np.float32 and len(pcm) % SR == 0
                      and np.isfinite(pcm).all(), key + ": invalid PCM shape/type/values")
                check("provenance", _sha(directory / "audio.npz") == summary["input_sha256"]
                      and _sha(directory / "measurements.npz") == summary["measurements_sha256"],
                      key + ": archive hashes differ from original summary")
                check("provenance", hashlib.sha256(pcm.tobytes()).hexdigest() == labels["pcm_sha256"]
                      and pcm.nbytes == labels["pcm_bytes"], key + ": PCM bytes differ from label digest")
                check("software", labels["group"] + "-" + labels["cell"] == key
                      and labels["split"] == split and labels["decision_sample"] == len(pcm)
                      and labels["sample_rate"] == SR, key + ": labels disagree with session")
                check("software", len(records) == len(routes) * 3 and
                      {(r["route"], r["condition"]) for r in records} ==
                      {(r, c) for r in routes for c in CONDITIONS}, key + ": incomplete route/control grid")
                expected_unit = np.repeat(np.arange(total), 10)
                expected_t = np.arange(frames) * .1 + .05
                shapes = {"t": (frames,), "unit": (frames,), "rms": (frames,), "power": (frames, 81),
                          "chroma": (frames, 12), "mert6": (frames, 768), "mert12": (frames, 768)}
                check("software", set(state) == set(shapes) and
                      all(state[name].shape == shape and np.isfinite(state[name]).all()
                          for name, shape in shapes.items()), key + ": malformed acoustic state")
                check("evidence", np.array_equal(state["unit"], expected_unit)
                      and _near(state["t"], expected_t, 1e-10), key + ": nonconsecutive measurement support")
                check("access", set(ceiling) == {"t", "unit", "rms", "clean"}
                      and ceiling["clean"].shape == (frames, 129), key + ": malformed separate clean archive")
                check("evidence", np.array_equal(ceiling["unit"], expected_unit)
                      and _near(ceiling["t"], expected_t, 1e-10), key + ": clean support differs")
                clean_expected = np.zeros((frames, 129), np.float32)
                clean_expected[:, 128] = 1
                occupancy = np.zeros(frames)
                for a, b, pitch in labels["all_rendered_events"]:
                    keep = (ceiling["t"] >= a) & (ceiling["t"] < b)
                    clean_expected[keep, 128] = 0
                    clean_expected[keep, int(pitch)] = 1
                    occupancy[keep] = .1
                check("evidence", np.array_equal(ceiling["clean"], clean_expected)
                      and np.array_equal(ceiling["rms"], occupancy), key + ": ceiling differs from saved independent score")
                source_on, source_off = labels["source_onset"], labels["source_offset"]
                source_overlap = (state["unit"] < source_off) & (state["unit"] + 1 > source_on)
                source_frames = (state["t"] >= source_on) & (state["t"] < source_off)
                check("evidence", np.any(source_frames) and summary["source_frame_count"] == int(sum(source_frames))
                      and summary["source_units_retained"] == np.unique(state["unit"][source_frames]).tolist(),
                      key + ": source coverage accounting differs")
                check("evidence", set(np.unique(state["unit"][source_overlap])) ==
                      set(range(math.floor(source_on), math.ceil(source_off))), key + ": incomplete source context coverage")
                check("eviction", len(arrivals) == total, key + ": missing arrived units")
                previous_received = -math.inf
                simulated = 0.
                for unit, log in enumerate(arrivals):
                    context = [unit * SR, (unit + 1) * SR]
                    check("evidence", log["unit"] == unit and log["context_samples"] == context
                          and log["audio_available_after_sample"] == context[1], key + f": wrong unit {unit} context")
                    check("evidence", previous_received <= log["broker_sent_monotonic"] <= log["arrived_monotonic"]
                          <= log["serialized_monotonic"] <= log["broker_received_monotonic"],
                          key + f": unit {unit} availability backdated or reordered")
                    previous_received = log["broker_received_monotonic"]
                    check("evidence", _near(log["roundtrip_seconds"], log["broker_received_monotonic"] - log["broker_sent_monotonic"])
                          and 0 <= log["spectral_seconds"] + log["mert_seconds"] <= log["roundtrip_seconds"] + 1e-8,
                          key + f": unit {unit} elapsed measurements disagree")
                    simulated = max(unit + 1, simulated) + log["roundtrip_seconds"]
                    check("evidence", _near(simulated, log["real_time_simulated_available_seconds"]),
                          key + f": unit {unit} virtual availability differs")
                    chunks = min(unit + 1, 4)
                    check("eviction", log["ring_chunks"] == chunks and
                          log["raw_ring_bytes"] == chunks * SR * 4 and
                          log["raw_ring_start_sample"] == max(0, unit - 3) * SR,
                          key + f": unit {unit} raw ring disagrees with bounded FIFO")
                    payload = sum(value.nbytes for value in state.values()) * (unit + 1) / total
                    check("access", payload <= log["retained_state_bytes"] <= 8 * 1024**2,
                          key + f": unit {unit} persistent size omits payload or exceeds cap")
                finish = summary["finish"]
                check("eviction", finish["raw_ring_start_sample"] == max(0, total - 4) * SR
                      and finish["raw_ring_bytes"] == min(total, 4) * SR * 4
                      and finish["raw_ring_start_sample"] > source_off * SR
                      and summary["source_pcm_evicted"] is True,
                      key + ": original source PCM not demonstrably evicted")
                onset_unit = int(math.floor(labels["query_onset"]))
                check("eviction", arrivals[onset_unit]["raw_ring_start_sample"] >= source_off * SR,
                      key + ": source PCM remained when query began arriving")
                check("access", finish["peak_state_bytes"] == max(x["retained_state_bytes"] for x in arrivals)
                      and finish["peak_state_bytes"] <= 8 * 1024**2
                      and sum(v.nbytes + sys.getsizeof(v) for v in ceiling.values()) < 8 * 1024**2,
                      key + ": persistent/clean state budget evidence failed")
                check("evidence", finish["unit_replacements"] == max(0, total - 60),
                      key + ": FIFO replacement count differs")
                preservation = _spectral_reconstruction(pcm, state)
                check("preservation", preservation["pass"], key + ": independently reconstructed sidecar differs")
                check("software", len(sequence) == 2 * len(records), key + ": commitment log size differs")
                for index, record in enumerate(records):
                    route, condition = record["route"], record["condition"]
                    prefix = key + "/" + route + "/" + condition
                    prediction = record["prediction"]
                    response_line, label_line = sequence[2 * index:2 * index + 2]
                    without_labels = {k: v for k, v in record.items() if k != "labels"}
                    check("evidence", response_line["type"] == "response" and label_line["type"] == "labels"
                          and response_line["value"] == without_labels and label_line["value"] == labels
                          and record["labels"] == labels, prefix + ": response not committed before matching labels")
                    check("evidence", previous_received <= prediction["committed_monotonic"]
                          <= prediction["broker_received_monotonic"]
                          and 0 <= prediction["compute_seconds"] <= prediction["readout_roundtrip_seconds"] + 1e-8,
                          prefix + ": prediction availability/compute clock failed")
                    check("evidence", _near(prediction["decision_latency_seconds"],
                          max(0, simulated - labels["query_offset"]) + prediction["readout_roundtrip_seconds"]),
                          prefix + ": reported decision latency differs from availability rule")
                    original = ceiling if route == "ceiling" else state
                    if condition == "full":
                        mask = np.ones(frames, bool)
                    elif condition == "recent":
                        mask = original["unit"] >= total - 4
                    else:
                        mask = ~((original["unit"] < source_off) & (original["unit"] + 1 > source_on))
                    sub = {name: value[mask] for name, value in original.items()}
                    if condition != "full":
                        check("access", not np.any((sub["unit"] < source_off) & (sub["unit"] + 1 > source_on)),
                              prefix + ": sanitized state still contains source context")
                    h = prediction["hypothesis"]
                    if h is None:
                        check("software", prediction["distance"] is None, prefix + ": unavailable hypothesis has distance")
                        continue
                    distance = prediction["distance"]
                    check("software", isinstance(distance, (int, float)) and math.isfinite(distance) and 0 <= distance <= 2,
                          prefix + ": invalid alignment distance")
                    path = np.asarray(h["path"])
                    path_valid = (path.ndim == 2 and path.shape[1] == 2 and len(path) > 0 and
                                  np.issubdtype(path.dtype, np.integer) and np.all(path >= 0) and np.all(path < len(sub["t"])))
                    if not check("evidence", path_valid, prefix + ": path indices invalid for sanitized state"):
                        continue
                    q, hist = path[:, 0], path[:, 1]
                    loud = np.flatnonzero(sub["rms"] > 1e-4)
                    if not check("evidence", len(loud) > 0, prefix + ": query without observed occupancy"):
                        continue
                    end = sub["t"][loud[-1]]
                    qi = np.flatnonzero((sub["t"] > end - 2 + 1e-8) & (sub["t"] <= end + 1e-8))
                    check("evidence", len(qi) >= 12 and q[0] == qi[0] and q[-1] == qi[-1]
                          and set(q).issubset(set(qi)), prefix + ": path uses unobserved/different query bins")
                    steps = {tuple(map(int, x)) for x in np.diff(path, axis=0)}
                    check("evidence", steps.issubset({(1, 1), (1, 2), (2, 1)}), prefix + ": forbidden DTW path step")
                    history_times = sub["t"][hist[0]:hist[-1] + 1]
                    check("evidence", np.all(np.diff(history_times) < .10001), prefix + ": path spans removed context hole")
                    qcontext = [int(sub["unit"][qi[0]]), int(sub["unit"][qi[-1]]) + 1]
                    hcontext = [int(sub["unit"][hist[0]]), int(sub["unit"][hist[-1]]) + 1]
                    check("access", hcontext[1] <= qcontext[0] and np.all(sub["unit"][hist] < qcontext[0]),
                          prefix + ": historical context overlaps query context")
                    check("evidence", prediction["query_context_support"] == qcontext
                          and prediction["history_context_support"] == hcontext
                          and _near(prediction["query_support"], [sub["t"][qi[0]] - .05, sub["t"][qi[-1]] + .05])
                          and _near([h["start"], h["end"]], [sub["t"][hist[0]] - .05, sub["t"][hist[-1]] + .05]),
                          prefix + ": reported support differs from actual path/unit support")
                    check("evidence", _near(h["stretch"], len(qi) * .1 / (h["end"] - h["start"]))
                          and .65 <= h["stretch"] <= 1.5 and isinstance(h["shift"], int) and -5 <= h["shift"] <= 5,
                          prefix + ": transformation differs from alignment/search semantics")
                    center = (h["start"] + h["end"]) / 2
                    if condition != "full" and source_on <= center < source_off:
                        check("evidence", False, prefix + ": removed source location recovered without its records")
                    # Recognition misses remain scientific outcomes, never validator errors.
                    if condition == "full" and not source_on <= center < source_off and record["cell"] != "foil":
                        behavioral_warnings.append({"session": key, "route": route,
                                                    "observation": "Candidate center outside source; scored by analyzer"})
                details.append({"session": key, "units": total, "frames": frames,
                                "source_frame_count": int(sum(source_frames)),
                                "source_context_units": np.unique(state["unit"][source_overlap]).tolist(),
                                "peak_persistent_bytes": finish["peak_state_bytes"],
                                "raw_ring_max_chunks": max(r["ring_chunks"] for r in arrivals),
                                "unit_replacements": finish["unit_replacements"],
                                "preservation": preservation,
                                "validation_seconds": time.perf_counter() - session_started})
            except Exception as exc:
                check("software", False, key + ": " + type(exc).__name__ + ": " + str(exc))
        canonical = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False)
        check("software", sorted(map(canonical, gathered_records)) == sorted(map(canonical, top_records)),
              "Aggregate records differ from immutable session records")
        check("software", sorted(map(canonical, gathered_summaries)) == sorted(map(canonical, top_summaries)),
              "Aggregate summaries differ from session summaries")
    except Exception as exc:
        check("software", False, "Split validation: " + type(exc).__name__ + ": " + str(exc))
    checks = {name: not issues[name] for name in CATEGORIES}
    # Missing/unfinished artifacts must not manufacture passes for other checks.
    if len(details) != expected_sessions:
        for name in CATEGORIES:
            if name != "software":
                issues[name].append("Incomplete session validation; evidence unavailable")
                checks[name] = False
    checks.update(expected_groups=expected_groups,
                  routes={route: {k: checks[k] for k in CATEGORIES if k != "preservation" or route != "ceiling"}
                          for route in sorted(validated_routes)})
    result = {**checks, "schema_version": 1, "split": split, "passed": all(checks[k] for k in CATEGORIES),
              "expected_sessions": expected_sessions, "validated_sessions": len(details), "issues": issues,
              "sessions": details, "behavioral_observations": behavioral_warnings,
              "source_hashes": source_hashes,
              "code_hashes": {name: _sha(root / name) for name in
                              ("listener.py", "runner.py", "features.py", "matching.py", "validate.py") if (root / name).exists()},
              "limitations": ["File/API access isolation is established by audited code plus saved effects, not an OS adversarial sandbox.",
                              "Commit ordering is independently checked in the fsynced append log; filesystem metadata alone is not a cryptographic timestamp.",
                              "Recognition and transformation accuracy are separate frozen-analyzer outcomes."],
              "validation_compute_seconds": time.perf_counter() - started,
              "predictor_or_encoder_executions": 0, "new_audio_sessions": 0}
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("splitdir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.splitdir)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
