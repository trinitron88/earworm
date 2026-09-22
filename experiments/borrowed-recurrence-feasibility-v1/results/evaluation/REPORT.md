# Borrowed recurrence feasibility — evaluation

**Decision C.** The clean ceiling does not pass the corresponding comparison; reconsider correspondence/test design before adding a memory controller.

Selected MERT candidate: mert12. Selected adequate audio route: none.

These are isolated rendered Bach score figures and newly composed motifs. Construction correspondence is not human perceptual identity. Each source occurred once, followed by 32 seconds of intervening music and actual eviction from the four-second raw buffer. Query selection uses the last two seconds of observed sound; source/query boundaries and note labels never enter the audio listener.

| Route | Unchanged identity | Transposed identity | Stretched identity | Foil false acceptance | Qualifies |
|---|---:|---:|---:|---:|---|
| standard | 100.0% [100.0%, 100.0%] | 75.0% [50.0%, 93.8%] | 75.0% [50.0%, 93.8%] | 12.5% [0.0%, 31.2%] | False |
| mert12 | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 25.0% [6.2%, 50.0%] | 0.0% [0.0%, 0.0%] | False |
| ceiling | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | False |

Brackets are paired-family bootstrap 95% intervals, not population guarantees. Full metrics by cell, stratum and memory condition are in `analysis.json`; intervals crossing acceptance thresholds remain visible.

## Transformation and memory benefit

| Route | Joint transposition | Joint stretch | Full − recent identity | Full − source removal identity |
|---|---:|---:|---:|---:|
| standard | 18.8% [0.0%, 37.5%] | 31.2% [12.5%, 56.2%] | 83.3% [72.9%, 93.8%] | 83.3% [72.9%, 93.8%] |
| mert12 | 0.0% [0.0%, 0.0%] | 12.5% [0.0%, 31.2%] | 41.7% [35.4%, 50.0%] | 41.7% [35.4%, 50.0%] |
| ceiling | 75.0% [50.0%, 93.8%] | 75.0% [50.0%, 93.8%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |

## Evidence, preservation and limits

Validation checks: `{"access": true, "eviction": true, "evidence": true, "expected_groups": 16, "preservation": true, "provenance": true, "selected_mert": "mert12", "software": true}`.

Conservatively charged executions/probes: 1000/1000, including 960 actual music readouts and a 40-probe qualification charge. Aggregate compute charge: 3659.4/7200 seconds. Package files at analysis: 606,135,712 bytes; spending $0. Source download: 123,847 bytes. Publication accounting is saved separately.

Peak listener RSS: 991,821,824 bytes, including fixed encoder, transient work and state. There was **no FIFO capacity pressure**; this is delay/interference retention under a cap, not demonstrated resistance to replacement.

The MERT route is a hybrid: correspondence uses frozen MERT features, while shift estimation uses the shared acoustic sidecar. The standard route is a disclosed FFT/trailing-smoothing CENS variant with the FMP unweighted step-skipping DTW. Failure can reflect the limited query window, observation features, alignment or rejection; it does not prove an encoder contains no musical relationships.

| Route | Max latency (s) | Max RTF | Persistent bytes (upper bound) |
|---|---:|---:|---:|
| standard | 1.2455 | 0.0026 | 2,871,989 |
| mert12 | 1.2422 | 0.0350 | 2,871,989 |
| ceiling | 1.1694 | 0.0002 | 221,864 |

Failed gates:

- **standard:** identity/transpose/all, identity/transpose/novel, identity/stretch/all, identity/stretch/bach, identity/stretch/novel, joint/transpose, joint/stretch, foil_false_accept
- **mert12:** identity/transpose/all, identity/transpose/bach, identity/transpose/novel, identity/stretch/all, identity/stretch/bach, identity/stretch/novel, joint/transpose, joint/stretch
- **ceiling:** joint/transpose, joint/stretch

Invalid reasons: none.
Missing evidence: none.

## Absolute realization evidence

The following saved table retains absolute spectral register, energy and timing beside invariant lookup. Spectral-register centroid is power-weighted on the logarithmic frequency axis; it is not a fundamental-pitch estimate. Frame summaries weight actual overlap duration with each construction interval. These values do not determine acceptance. Full timestamped bins, including source evidence after raw-audio eviction, remain in every `measurements.npz`.

| Cell | Mean spectral-centroid change (semitone units) | Mean RMS ratio | Mean query/source duration |
|---|---:|---:|---:|
| unchanged | -0.0036 | 0.9974 | 1.0000 |
| transpose | -0.0168 | 0.9974 | 1.0000 |
| stretch | -0.0146 | 0.9963 | 1.0250 |
| foil | -0.1459 | 0.9974 | 1.0000 |

Signed transposition averages can cancel because shifts are balanced; consult each family in `realization-evidence.json` to see the retained change.

## Review and next action

Review the exact publication head and execution freeze, saved predictions committed before labels, archived inputs/measurements, independent validation, all negative outcomes and resource ledger. Stop for the existing reviewer’s A/B/C/INVALID disposition. No automatic repair, new experiment, controller, training or paid compute follows this report.
