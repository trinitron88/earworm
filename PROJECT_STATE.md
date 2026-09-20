# Project Earworm

Earworm's finish line is a reusable, stateful listener for continuous musical audio. Under explicit memory, compute and latency budgets, its auditory past should improve forecasts; recurring relationships should remain recognizable while changes in their realization remain distinguishable. Captured evidence, derived measurements, revisable interpretations and pre-outcome expectations must remain separate. Agents stay outside the listening loop. Musical appreciation remains an open question.

**Top goal: long-term recognition of transformed musical material.** Hear a phrase once, retain it through substantial intervening music and actual recent-buffer eviction, then identify its earlier occurrence and transformation—transposition, inversion, rhythmic stretching or another voice—while rejecting similar unrelated phrases. Recognition and transformation detection are separate abilities. Bach fugues are the first substantial musical target, progressing through figures/isolated voices, combined voices, complete fugues and different performances, then broader traditions; this is not a permanent genre restriction.

## Current evidence and decision

The final within-event aggregation test is complete and awaiting exact-head review. **Branch C: reject this approach and end localized crop/within-event repairs.** Combining short-window pitch observations gave nearly the same measurement accuracy as trim16 and identical intact reference scores. Its separate uncertainty mixture regressed to40/48 joint predictions versus46/48 for trim16; oracle-boundary remained48/48 throughout. It also failed ambiguity and rendering-family safety gates.

This result concerns the declared aggregation policies and conservative probability mixture, not every possible uncertainty-aware listener. Original PCM, all window evidence and historical observations remain separate from interpretation. No continuous-listening front is accepted. These remain synthetic short-buffer experiments without eviction or natural-music transfer.

- [Current report](experiments/causal-event-aggregation-v1/REPORT.md)
- [Decision](experiments/causal-event-aggregation-v1/results/heldout/decision.json)
- [All model/path/control results](experiments/causal-event-aggregation-v1/results/heldout/summary.csv)
- [Validation](experiments/causal-event-aggregation-v1/validation/heldout.json)
- [Prior trim16 evidence](experiments/event-window-repair-v1/REPORT.md)

## Finite capability checklist

| Capability | Evidence status | Remaining acceptance requirement |
|---|---|---|
| Continuous input and causal event/voice organization | Chunk-only API/timing validated; trim/aggregation sequence ended without adoption | Pass frozen prediction, event, uncertainty and safety gates without supplied boundaries |
| History-improved calibrated forecasts at multiple meaningful horizons | Single-step synthetic supplied-boundary prediction demonstrated | Fresh non-overlapping horizon tests against strong present/transition/retrieval baselines |
| Long-term transformed recognition | Early short-history transformation evidence only | Separate transformations, actual recent-buffer eviction, all accessible storage counted, unfamiliar motifs and relevant-memory removal |
| Retain realization details and detect change | Early controlled edit/representation evidence | Report recognition and retained pitch/timbre/rhythm detail separately for declared interference delays |
| Uncertainty, contradiction and recovery | Controlled ambiguity checks only | Preserve immutable evidence, revise interpretations when new sound contradicts expectations, avoid silently filling missing audio |
| Session continuity and bounded execution | Per-run causal logs and bounded short buffers | Save/restore listening state; distinguish captured silence from missing samples; measure actual availability and storage/compute |
| Held-out musical transfer | Not established | Piece/motif-family-separated material, progressing from isolated Bach figures/voices to combined voices and complete fugues/different performances |

## First-release acceptance plan

A reusable listener release must expose a continuous PCM input and persistent listening-state interface, with explicit measured memory/compute/latency limits, immutable evidence references and separately labeled measurements/interpretations/forecasts. It must pass **all six functional rows above**, on fresh controlled interventions and independently reviewed held-out musical material appropriate to its declared scope. A combined score cannot hide lost detail, failed calibration or forgetting. The substantial Bach milestone additionally requires the seventh row's progression; success on isolated voices cannot be advertised as complete-fugue listening.

The PM must freeze concrete thresholds, datasets, horizons and delays in bounded assignments before each acceptance test. This checklist is a finite release gate, not authorization for seven immediate experiments or an open-ended audit sequence. No release is currently accepted. The next unresolved prerequisite is a reliable event representation; subsequent stages require explicit PM assignments after review.

## Preserved history and next action

PR #10's supplied-boundary observation repair passed its scoped test; PR #9 identified the octave-anchor prerequisite; PR #8 selected the simpler transformation-aware retrieval reference. E08 ranking and acceptance remain distinct results. PR #11 established the event-window prerequisite; all540 prior artifacts are preserved.

- [Observation repair](experiments/fundamental-observation-repair-v1/REPORT.md)
- [Controlled robustness](experiments/controlled-motif-robustness-v1/REPORT.md)
- [History prediction](experiments/history-prediction-v1/REPORT.md)
- [Original E08 state](review/experiment08/original-snapshot-PROJECT_STATE.md)

Publish this complete snapshot and stop for review. Branch C ends further crop/within-event aggregation micro-repairs. After review the PM may explicitly assign a different event representation or checkpoint a concrete blocker under the decision filter. No follow-on study is assigned here; no adoption, complexity increase, spending, MERT changes, historical rewrite or worker merge.
