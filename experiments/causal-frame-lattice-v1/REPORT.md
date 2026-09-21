# Frame lattice: development blocked before the first forecast

**Invalid execution; no scientific conclusion about the lattice.** The first development stream stopped when NumPy's median operation attempted a lazy module import after the listener's filesystem guard was active. The guard correctly raised `PermissionError: No filesystem/network/process access`; the broker then reported `RuntimeError: Worker failed`.

No policy was selected. No forecast was committed, no target was revealed, and calibration and held-out evaluation never started. There was no rerun, guard relaxation, replacement group, post-failure model change, paid fallback or new experiment.

## What was prepared

The implementation declares three fixed-cadence lattices:32/48/64 ms completed windows with8 ms hops. The lattice path uses no note-event boundaries, crops or aggregates. Frozen event-based fronts remain separate comparators. A bounded monotone sequence matcher compares a fixed recent24-frame query with earlier19/24/29-frame sequences, reports absolute and uniform-offset matches, and forecasts from earlier continuations. Captured frame features retain pitch candidates, spectral shape, energy, indices, hashes and availability/computation timestamps.

The protocol adds the requested similar-unrelated control and one save/restore probe per group. It declares40 fresh groups (8/8/24), excluding229 prior normalized identities, up to1,000 total streams including probes. Recognition, transformation estimates and forecast scoring are separated. Nonzero pitch transposition is not tested in this controlled design; changed-condition labels concern timing with zero true pitch offset, and timbre/energy residuals are reported separately. All of this is **prepared code, not demonstrated capability**.

Declared development execution commit: `9708e34e0f445c23f99b9420a5d9c50e0d95e537`. Exact base: `5aa6396fb680012efb6dad5fd7ae50801a4afd99`. Protocol and implementation were committed before the attempt. There is no held-out freeze/preregistration receipt because development never reached selection. Publication is a separate commit identified by the PR and completion receipt.

## Saved evidence and missing outputs

The failure log contains44 valid chained records: one start,21 chunk dispatch/arrival pairs, and the first forecast-dispatch record. The listener received21,504 samples (1.344 seconds) in21 chunks. There is no forecast commitment, oracle commitment, reveal or score. `STARTED.json` and the original execution sources/configuration remain intact.

The waveform, truth and forecast cache gzip files are valid but empty: this broker writes those records after a completed forecast, which was never reached. Per-split final runtime/extraction counters, recipe exports, future-invariance checks and save/restore outcomes were also not written. Those gaps are explicit; we did not reconstruct or regenerate missing evidence. The first group's20 development episode waveforms were constructed in the broker before its first stream; only one stream entered the worker. The ledger retains the full200-stream development reservation. Calibration200 and heldout600 reservations were not launched. Exact completed extraction counts cannot be recovered from the terminated worker, so no validated compute benchmark or full resource-validity claim is made.

[Failure record](failure.json), [decision](results/decision.json), [saved-failure validation](validation/failure.json), [original start](data/development/STARTED.json), [stream reservation](run_ledger.json).

## Saved-only checks

The validator checks all44 hash-chain records, absence of committed outputs/reveals, intact empty caches, absence of calibration/heldout directories, execution-source hashes against the declared commit, and645 unchanged historical file hashes. These checks verify the preserved failure evidence; they do **not** make the experiment scientifically valid. Recognition, rejection, transformation, prediction, calibration, latency, save/restore and uncertainty gates remain untested.

```sh
python experiments/causal-frame-lattice-v1/validation/failed_development.py
```

This performs no acoustic extraction or listener execution. Do not run `run.py` again: its STARTED guard preserves the failed attempt and prevents repeating the stream. The original guarded implementation is included unchanged for review, along with the intended analysis/validation code, recipes and split manifest. None of those intended checks is represented as having passed on missing outputs.

## Decision and stop

Publish this complete failure snapshot and await review under the assignment's invalid/inconclusive stop rule. The concrete runtime prerequisite is arranging necessary numerical-library initialization before installing the filesystem guard, while retaining the guard throughout listening. That is an unexecuted repair proposal; the PM must explicitly bound any next action and reconcile this failed attempt before authorizing further execution.

This result says nothing about whether a frame lattice can hear, recognize or forecast musical figures. Historical negative evidence against crop/within-event repairs remains unchanged. No perceptual identity, natural-music, polyphony, memory eviction or long-term transformed-recognition claim follows. Spending is zero and MERT is unchanged.
