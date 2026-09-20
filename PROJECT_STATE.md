# Project Earworm

Earworm's finish line is a reusable, stateful listener for continuous musical audio. Under explicit memory, compute and latency budgets, its auditory past should improve forecasts; recurring relationships should remain recognizable while changes in their realization remain distinguishable. Captured evidence, derived measurements, revisable interpretations and pre-outcome expectations must remain separate. Agents stay outside the listening loop. Musical appreciation remains an open question.

**Top goal: long-term recognition of transformed musical material.** Hear a phrase once, retain it through substantial intervening music and actual recent-buffer eviction, then identify its earlier occurrence and transformation—transposition, inversion, rhythmic stretching or another voice—while rejecting similar unrelated phrases. Recognition and transformation detection are separate abilities. Bach fugues are the first substantial musical target, progressing through figures/isolated voices, combined voices, complete fugues and different performances, then broader traditions; this is not a permanent genre restriction.

## Current evidence and decision

The event-window repair is complete and awaiting exact-head review. **Branch B: measurements improved, adoption withheld.** A frozen 16 ms interior trim improved pitched-event accuracy from72.8% to97.0% and joint reference prediction from14/48 to45/48 on fresh held-out groups. The evaluator-only supplied-boundary ceiling remained48/48 in every cell.

The repair passed event and latency gates but failed noninferiority, joint Brier-score tolerance, ambiguity controls and the fundamental-rendering safety family. Better pitch measurements did not fully recover reliable uncertainty or forecasting. Original captured audio, observations and whole-event bounds remain separately preserved. This is synthetic monophonic, short-buffer evidence with no eviction; no natural-music or long-term-memory capability is established.

- [Current report](experiments/event-window-repair-v1/REPORT.md)
- [Decision and adoption gates](experiments/event-window-repair-v1/results/heldout/decision.json)
- [All model/control results](experiments/event-window-repair-v1/results/heldout/summary.csv)
- [Validation](experiments/event-window-repair-v1/validation/heldout.json)

## Finite capability checklist

| Capability | Evidence status | Remaining acceptance requirement |
|---|---|---|
| Continuous input and causal event/voice organization | Chunk-only API/timing validated; interior support improves pitch, adoption gates still fail | Pass frozen prediction, event, uncertainty and safety gates without supplied boundaries |
| History-improved calibrated forecasts at multiple meaningful horizons | Single-step synthetic supplied-boundary prediction demonstrated | Fresh non-overlapping horizon tests against strong present/transition/retrieval baselines |
| Long-term transformed recognition | Early short-history transformation evidence only | Separate transformations, actual recent-buffer eviction, all accessible storage counted, unfamiliar motifs and relevant-memory removal |
| Retain realization details and detect change | Early controlled edit/representation evidence | Report recognition and retained pitch/timbre/rhythm detail separately for declared interference delays |
| Uncertainty, contradiction and recovery | Controlled ambiguity checks only | Preserve immutable evidence, revise interpretations when new sound contradicts expectations, avoid silently filling missing audio |
| Session continuity and bounded execution | Per-run causal logs and bounded short buffers | Save/restore listening state; distinguish captured silence from missing samples; measure actual availability and storage/compute |
| Held-out musical transfer | Not established | Piece/motif-family-separated material, progressing from isolated Bach figures/voices to combined voices and complete fugues/different performances |

## First-release acceptance plan

A reusable listener release must expose a continuous PCM input and persistent listening-state interface, with explicit measured memory/compute/latency limits, immutable evidence references and separately labeled measurements/interpretations/forecasts. It must pass **all six functional rows above**, on fresh controlled interventions and independently reviewed held-out musical material appropriate to its declared scope. A combined score cannot hide lost detail, failed calibration or forgetting. The substantial Bach milestone additionally requires the seventh row's progression; success on isolated voices cannot be advertised as complete-fugue listening.

The PM must freeze concrete thresholds, datasets, horizons and delays in bounded assignments before each acceptance test. This checklist is a finite release gate, not authorization for seven immediate experiments or an open-ended audit sequence. No release is currently accepted. The next unresolved prerequisite is event-window formation; subsequent stages require explicit PM assignments after review.

## Preserved history and next action

PR #10's supplied-boundary observation repair passed its scoped test; PR #9 identified the octave-anchor prerequisite; PR #8 selected the simpler transformation-aware retrieval reference. E08 ranking and acceptance remain distinct results. PR #11 established the event-window prerequisite; all446 prior artifacts are preserved.

- [Observation repair](experiments/fundamental-observation-repair-v1/REPORT.md)
- [Controlled robustness](experiments/controlled-motif-robustness-v1/REPORT.md)
- [History prediction](experiments/history-prediction-v1/REPORT.md)
- [Original E08 state](review/experiment08/original-snapshot-PROJECT_STATE.md)

Publish this one complete snapshot and stop for review. No further experiment is assigned here. The continuously authorized PM may choose a different localized event/measurement approach only if evidence supports a concrete discriminating decision, through an explicit bounded assignment. No adoption, complexity increase, old estimator audit, spending, MERT change, historical rewrite or worker merge is authorized by this result.
