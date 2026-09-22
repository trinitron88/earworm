# Borrowed recurrence feasibility — development

**Decision C.** The clean ceiling does not pass the corresponding comparison; reconsider correspondence/test design before adding a memory controller.

Selected MERT candidate: mert12. Selected adequate audio route: none.

These are isolated rendered Bach score figures and newly composed motifs. Construction correspondence is not human perceptual identity. Each source occurred once, followed by 32 seconds of intervening music and actual eviction from the four-second raw buffer. Query selection uses the last two seconds of observed sound; source/query boundaries and note labels never enter the audio listener.

| Route | Unchanged identity | Transposed identity | Stretched identity | Foil false acceptance | Qualifies |
|---|---:|---:|---:|---:|---|
| standard | 100.0% [100.0%, 100.0%] | 87.5% [62.5%, 100.0%] | 75.0% [50.0%, 100.0%] | 0.0% [0.0%, 0.0%] | False |
| mert12 | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 25.0% [0.0%, 62.5%] | 0.0% [0.0%, 0.0%] | False |
| ceiling | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 0.0% [0.0%, 0.0%] | False |

Brackets are paired-family bootstrap 95% intervals, not population guarantees. Full metrics by cell, stratum and memory condition are in `analysis.json`; intervals crossing acceptance thresholds remain visible.

## Transformation and memory benefit

| Route | Joint transposition | Joint stretch | Full − recent identity | Full − source removal identity |
|---|---:|---:|---:|---:|
| standard | 37.5% [12.5%, 75.0%] | 75.0% [50.0%, 100.0%] | 87.5% [70.8%, 100.0%] | 87.5% [70.8%, 100.0%] |
| mert12 | 0.0% [0.0%, 0.0%] | 12.5% [0.0%, 37.5%] | 41.7% [33.3%, 54.2%] | 41.7% [33.3%, 54.2%] |
| ceiling | 87.5% [62.5%, 100.0%] | 75.0% [50.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] |

## Evidence, preservation and limits

Validation checks: `{"access": true, "eviction": true, "evidence": true, "expected_groups": 8, "preservation": true, "provenance": true, "selected_mert": "mert12", "software": true}`.

Conservatively charged executions/probes: 424/1000, including 384 actual music readouts and a 40-probe qualification charge. Aggregate compute charge: 2824.7/7200 seconds. Package files at analysis: 206,031,039 bytes; spending $0. Source download: 123,847 bytes. Publication accounting is saved separately.

Peak listener RSS: 992,296,960 bytes, including fixed encoder, transient work and state. There was **no FIFO capacity pressure**; this is delay/interference retention under a cap, not demonstrated resistance to replacement.

The MERT route is a hybrid: correspondence uses frozen MERT features, while shift estimation uses the shared acoustic sidecar. The standard route is a disclosed FFT/trailing-smoothing CENS variant with the FMP unweighted step-skipping DTW. Failure can reflect the limited query window, observation features, alignment or rejection; it does not prove an encoder contains no musical relationships.

| Route | Max latency (s) | Max RTF | Persistent bytes (upper bound) |
|---|---:|---:|---:|
| standard | 1.2446 | 0.0026 | 2,871,989 |
| mert12 | 1.2364 | 0.0378 | 2,871,989 |
| ceiling | 1.1693 | 0.0002 | 221,864 |

Failed gates:

- **standard:** identity/transpose/novel, identity/stretch/all, identity/stretch/novel, joint/transpose, joint/stretch
- **mert12:** identity/transpose/all, identity/transpose/bach, identity/transpose/novel, identity/stretch/all, identity/stretch/bach, identity/stretch/novel, joint/transpose, joint/stretch
- **ceiling:** joint/stretch

Invalid reasons: none.
Missing evidence: none.

## Absolute realization evidence

The following saved table retains absolute spectral register, energy and timing beside invariant lookup. Spectral-register centroid is power-weighted on the logarithmic frequency axis; it is not a fundamental-pitch estimate. Frame summaries weight actual overlap duration with each construction interval. These values do not determine acceptance. Full timestamped bins, including source evidence after raw-audio eviction, remain in every `measurements.npz`.

| Cell | Mean spectral-centroid change (semitone units) | Mean RMS ratio | Mean query/source duration |
|---|---:|---:|---:|
| unchanged | 0.0055 | 0.9975 | 1.0000 |
| transpose | -0.0174 | 0.9975 | 1.0000 |
| stretch | -0.0448 | 0.9964 | 1.0250 |
| foil | -0.0595 | 0.9975 | 1.0000 |

Signed transposition averages can cancel because shifts are balanced; consult each family in `realization-evidence.json` to see the retained change.

## Review and next action

Review the exact publication head and execution freeze, saved predictions committed before labels, archived inputs/measurements, independent validation, all negative outcomes and resource ledger. Stop for the existing reviewer’s A/B/C/INVALID disposition. No automatic repair, new experiment, controller, training or paid compute follows this report.
