# Project Earworm

Earworm's finish line is a reusable, stateful listener for continuous musical audio. Under explicit memory, compute and latency budgets, its auditory past should improve forecasts; recurring relationships should remain recognizable while changes in their realization remain distinguishable. Captured evidence, derived measurements, revisable interpretations and pre-outcome expectations must remain separate. Agents stay outside the listening loop. Musical appreciation remains an open question.

**Top goal: long-term recognition of transformed musical material.** Hear a phrase once, retain it through substantial intervening music and actual recent-buffer eviction, then identify its earlier occurrence and transformation—transposition, inversion, rhythmic stretching or another voice—while rejecting similar unrelated phrases. Recognition and transformation detection are separate abilities. Bach fugues are the first substantial musical target, progressing through figures/isolated voices, combined voices, complete fugues and different performances, then broader traditions; this is not a permanent genre restriction.

## Current evidence and decision

**The support-consistent validation repair passes; the frozen f32 lattice fails its heldout advancement gates (branch C).** Independent reconstruction clears the four endpoint-only calibration frames without changing the listener or rerunning prior audio. The24 reserved heldout groups then ran once, with causal integrity, save/restore and timing checks passing.

Correct-source recognition was115/192 (59.9%). On combined changes, f32 forecasts were25/48 correct versus46/48 for the strongest frozen comparator; the paired difference was−43.75 percentage points (95% interval−60.42 to−27.08). Transformation, proper-score, ambiguity and family-safety gates also failed. This rejects the current fixed lattice/readout for advancement; it does not establish that continuous features contain no useful information. No continuous listener is accepted.

The complete successor is being published for exact-head review. Development/calibration evidence and outcomes, PR15, E08 and all763 historical artifacts remain unchanged. No nonzero-transposition, natural-music, polyphony, long-term-memory or appreciation claim follows.

- [Current report](experiments/frame-lattice-validation-repair-v1/REPORT.md)
- [Heldout decision](experiments/frame-lattice-validation-repair-v1/results/heldout/decision.json)
- [Validation correction](experiments/frame-lattice-validation-repair-v1/VALIDATION_CHANGE.md)
- [Integrity checks](experiments/frame-lattice-validation-repair-v1/validation/heldout.json)
- [Historical calibration stop](experiments/frame-lattice-init-repair-v1/REPORT.md)

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

PR #10's supplied-boundary observation repair passed its scoped test; PR #9 identified the octave-anchor prerequisite; PR #8 selected the simpler transformation-aware retrieval reference. E08 ranking and acceptance remain distinct results. PR #11 established the event-window prerequisite; all763 historical artifacts are preserved.

- [Observation repair](experiments/fundamental-observation-repair-v1/REPORT.md)
- [Controlled robustness](experiments/controlled-motif-robustness-v1/REPORT.md)
- [History prediction](experiments/history-prediction-v1/REPORT.md)
- [Original E08 state](review/experiment08/original-snapshot-PROJECT_STATE.md)

Publish the complete branch-C successor and stop awaiting review. The authorized validation correction and reserved heldout run are complete. The PM may assign a justified next bounded action after review; this report authorizes none. Do not return to boundary/window/crop/aggregation micro-repairs or infer adoption of a comparator. No new experiment, architecture change, spending, MERT change, historical rewrite or worker merge is started here.
