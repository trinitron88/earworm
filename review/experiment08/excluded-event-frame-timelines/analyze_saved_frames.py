"""Descriptive tables and scatter plots of saved frames; no fitting or note segmentation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def unpack(entry):
    dtype = np.dtype(entry["dtype_str"])
    a = np.asarray([0 if x is None else x for x in entry["values"]], dtype=dtype)
    for item in entry["nonfinite"]:
        a.view(np.uint8).reshape(-1, dtype.itemsize)[item["index"]] = np.frombuffer(bytes.fromhex(item["raw_bytes_hex"]), dtype=np.uint8)
    assert str(a.dtype) == entry["dtype"] and list(a.shape) == entry["shape"]
    assert hashlib.sha256(a.tobytes()).hexdigest() == entry["raw_bytes_sha256"]
    return a


def hz_to_semitones(hz):
    return 12 * math.log2(float(hz)/220) if hz is not None and math.isfinite(hz) and hz > 0 else None


def status(value):
    if value is None:
        return "array_absent"
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "+inf" if value > 0 else "-inf"
    return "finite_positive" if value > 0 else "finite_nonpositive"


def csv_write(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader();writer.writerows(rows)


def limits(values, positive=False):
    finite = [float(v) for v in values if math.isfinite(v) and (not positive or v > 0)]
    return (min(finite), max(finite)) if finite else (None, None)


def make_plots(events, out):
    plt.rcParams.update({"font.size": 9, "svg.hashsalt": "earworm-saved-frames", "axes.spines.top": False, "axes.spines.right": False})
    for page, start in enumerate(range(0, len(events), 5), 1):
        subset = events[start:start+5]
        fig, axes = plt.subplots(len(subset), 2, figsize=(12.5, 13), squeeze=False, constrained_layout=True)
        for row, e in enumerate(subset):
            arrays = {k:unpack(v) for k,v in e["arrays"].items()}
            x = arrays["frame_time_s"].astype(float)-e["onset_s"]
            duration = e["offset_s"]-e["onset_s"]
            ax, energy = axes[row]
            pitch = np.asarray([hz_to_semitones(float(v)) if math.isfinite(v) and v > 0 else np.nan for v in arrays["frame_pitch_hz"]])
            peak = np.asarray([hz_to_semitones(float(v)) if math.isfinite(v) and v > 0 else np.nan for v in arrays["frame_spectral_peak_hz"]])
            refined = arrays["frame_phase_refined"].astype(bool)
            finite = np.isfinite(pitch)
            ax.scatter(x[finite & refined], pitch[finite & refined], s=18, color="#167a85", label="Pitch: phase flag true")
            ax.scatter(x[finite & ~refined], pitch[finite & ~refined], s=24, facecolors="none", edgecolors="#167a85", label="Pitch: phase flag false")
            ax.scatter(x[np.isfinite(peak)], peak[np.isfinite(peak)], marker="x", s=20, color="#c7772a", label="Spectral peak")
            floor = min(np.nanmin(pitch),np.nanmin(peak))-1.1
            ax.scatter(x[~finite], np.full((~finite).sum(), floor), marker="|", s=70, color="#7f3434", label="No cached pitch")
            energy.scatter(x, arrays["frame_rms"], s=18, color="#41689d")
            for panel in (ax, energy):
                panel.axvspan(0,.018, color="#d4d9df", alpha=.5)
                panel.axvspan(duration-.018,duration, color="#d4d9df", alpha=.5)
                panel.set_xlim(0,duration)
                panel.grid(alpha=.18)
                panel.set_xlabel("Seconds after cached event onset")
            ax.set_ylabel("Semitones relative to 220 Hz")
            energy.set_ylabel("Saved RMS")
            ax.set_title(f"{e['query_id']} · event {e['event_index']}\nSaved bounds: {e['onset_s']:.6f}–{e['offset_s']:.6f} s", loc="left", fontsize=10)
            energy.set_title("Energy observations · same frames", loc="left", fontsize=10)
            if row == 0:
                ax.legend(fontsize=7, loc="best", framealpha=.85)
        fig.suptitle(f"Earworm · saved frame timelines · page {page}\nPoints only: no interpolation, smoothing, segmentation or memory expectations. Gray = frozen 18 ms edge context.", fontsize=12)
        fig.savefig(out/f"timelines-{page}.png", dpi=160, metadata={"Software":"Earworm saved-frame audit"})
        fig.savefig(out/f"timelines-{page}.svg", metadata={"Date":None, "Creator":"Earworm saved-frame audit"})
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("Use a new or empty output directory")
    args.out.mkdir(parents=True, exist_ok=True)
    identifiers = json.loads((HERE/"input_identifiers.json").read_text())
    for item in identifiers["exports"]:
        assert hashlib.sha256((HERE/item["path"]).read_bytes()).hexdigest() == item["sha256"]
    inventory = json.loads((HERE/"inventory.json").read_text())
    if inventory["status"] != "complete":
        raise ValueError("Essential or requested saved evidence unavailable; report inventory without regeneration")
    data = json.loads((HERE/"saved_frames.json").read_text())
    frame_rows, event_rows = [], []
    for e in data["events"]:
        a = {k:unpack(v) for k,v in e["arrays"].items()}
        times = a["frame_time_s"].astype(float)
        assert len(times) == len(e["original_frame_indices"]) and np.all(np.diff(times)>0)
        assert all(e["onset_s"] <= t <= e["offset_s"] for t in times)
        interior = (times >= e["interior_start_s"]) & (times <= e["interior_end_s"])
        for i,t in enumerate(times):
            values = {key:(a[key][i].item() if key in a else None) for key in data["fields"]}
            frame_rows.append({"query_id":e["query_id"], "event_index":e["event_index"],
                "frame_order_0_based":i, "original_frame_index":e["original_frame_indices"][i],
                "event_onset_s":e["onset_s"], "event_offset_s":e["offset_s"],
                "time_after_event_onset_s":float(t-e["onset_s"]), "inside_frozen_18ms_interior":bool(interior[i]),
                **values, "pitch_status":status(values["frame_pitch_hz"]), "spectral_peak_status":status(values["frame_spectral_peak_hz"]),
                "pitch_semitones_re_220hz":hz_to_semitones(values["frame_pitch_hz"]),
                "spectral_peak_semitones_re_220hz":hz_to_semitones(values["frame_spectral_peak_hz"])})
        valid = np.isfinite(a["frame_pitch_hz"]) & (a["frame_pitch_hz"] > 0)
        finite_indices = np.flatnonzero(valid)
        phase_indices = np.flatnonzero(valid & a["frame_phase_refined"])
        row = {"query_id":e["query_id"], "event_index":e["event_index"],
            "onset_s":e["onset_s"], "offset_s":e["offset_s"], "interior_start_s":e["interior_start_s"], "interior_end_s":e["interior_end_s"],
            "frame_n":len(times), "interior_frame_n":int(interior.sum()), "absent_array_n":len(e["absent_arrays"]),
            "voiced_true_n":int(a["frame_voiced"].sum()), "phase_refined_true_n":int(a["frame_phase_refined"].sum()),
            "finite_positive_pitch_n":int(valid.sum()), "nonfinite_pitch_n":int((~np.isfinite(a["frame_pitch_hz"])).sum()),
            "interior_voiced_n":int(a["frame_voiced"][interior].sum()), "interior_phase_refined_n":int(a["frame_phase_refined"][interior].sum()),
            "interior_finite_positive_pitch_n":int(valid[interior].sum()),
            "first_finite_pitch_time_s":float(times[finite_indices[0]]) if len(finite_indices) else None,
            "first_finite_pitch_hz":float(a["frame_pitch_hz"][finite_indices[0]]) if len(finite_indices) else None,
            "last_finite_pitch_time_s":float(times[finite_indices[-1]]) if len(finite_indices) else None,
            "last_finite_pitch_hz":float(a["frame_pitch_hz"][finite_indices[-1]]) if len(finite_indices) else None,
            "first_phase_refined_pitch_time_s":float(times[phase_indices[0]]) if len(phase_indices) else None,
            "first_phase_refined_pitch_hz":float(a["frame_pitch_hz"][phase_indices[0]]) if len(phase_indices) else None}
        for field in ("frame_rms", "frame_energy_dbfs", "frame_pitch_hz", "frame_spectral_peak_hz", "frame_spectral_centroid_hz"):
            low,high = limits(a[field]);row[field+"_min"]=low;row[field+"_max"]=high
            row[field+"_finite_n"]=int(np.isfinite(a[field]).sum())
        row["pitch_semitones_min"] = hz_to_semitones(row["frame_pitch_hz_min"])
        row["pitch_semitones_max"] = hz_to_semitones(row["frame_pitch_hz_max"])
        event_rows.append(row)
    assert len(event_rows)==10 and len(frame_rows)==380
    csv_write(args.out/"frames.csv",frame_rows);csv_write(args.out/"event_summary.csv",event_rows)
    summary={"events":len(event_rows),"frames":len(frame_rows),
        "interior_frames":sum(e["interior_frame_n"] for e in event_rows),
        "voiced_frames":sum(e["voiced_true_n"] for e in event_rows),
        "phase_refined_frames":sum(e["phase_refined_true_n"] for e in event_rows),
        "finite_positive_pitch_frames":sum(e["finite_positive_pitch_n"] for e in event_rows),
        "nonfinite_pitch_frames":sum(e["nonfinite_pitch_n"] for e in event_rows),
        "absent_arrays":sum(e["absent_array_n"] for e in event_rows),
        "pitch_hz_range":[min(e["frame_pitch_hz_min"] for e in event_rows),max(e["frame_pitch_hz_max"] for e in event_rows)],
        "unit_conversion":"12 * log2(Hz / 220), only for finite positive values; no missing value interpolation.",
        "interior_contract":"Inclusive [cached onset + .018, cached offset - .018]; descriptive context only. All in-bound frames remain in the export and tables.",
        "interpretation_boundary":"Frame pitch, spectral peak, voicing and phase flags are stored estimator outputs, not verified notes or confidence guarantees. No memory agreement score, winner, fitted segment or retrieval decision is produced."}
    (args.out/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    make_plots(data["events"],args.out)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
