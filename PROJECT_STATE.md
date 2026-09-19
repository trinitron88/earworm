# Project Earworm — current state

Updated September 19, 2026. This living overview is refreshed in every PR; original experiment records and prior audit packages remain historical evidence.

## Goal

Build auditory representation and memory that help AI systems hear, listen to and interpret music: retain what arrived, remember earlier sound, recognize relationships through changes, and use auditory history to anticipate what comes next. Observations must remain distinct from expectations. Human-like musical appreciation is a long-term ambition; no subjective experience is established here.

## Current phase and result

**The one authorized history-dependent prediction experiment is complete, awaiting review. Its frozen decision rule selects B: retain transformation-aware sequence retrieval as the prediction reference.** [Report](experiments/history-prediction-v1/REPORT.md) · [Selected reference](experiments/history-prediction-v1/selected_reference.json)

On 24 fresh held-out groups, the relational readout and transformation-aware retrieval each correctly predicted both continuations in every paired basic and transposed case. Histories contained the same sound-block bytes in different temporal relationships; the final two history blocks and present probe were identical. Transposed target pitches were unheard in the episode and training data.

Reset/removal removed the history advantage; swapping histories redirected forecasts; ambiguous histories retained approximately equal probabilities for their two futures. Forecasts were durably committed before reveal. The relational readout had zero measured transfer advantage, with paired group-bootstrap interval [0, 0], satisfying the predefined equivalence criterion on this sample. This supports controlled causal anticipation, not an advance beyond retrieval or universal equivalence.

The test uses clean synthetic monophonic blocks, supplied block boundaries and an explicit continuation rule. Natural music, polyphony, long-term memory and appreciation remain outside the demonstrated capability. MERT remains frozen and was unused in this experiment.

## What Experiment 08 established

- **Useful signal exists:** the correct stored phrase ranked uniquely first in 553/576 held-out queries. This is a ranking result, not a direct retention measure.
- **Accepted retrieval lagged:** the frozen reader accepted 164/576, versus 198/576 for the earlier reader. Calibration allowed at most 5% empirical absent-history false acceptance; this set recorded zero. It was not a zero-tolerance design.
- **Several losses remain distinct:** event eligibility excluded some broad-pitch events, feature aggregation omitted retained relationships, and calibrated acceptance rejected otherwise high-ranked candidates. No result establishes the gate as the sole cause.
- **Saved information exceeded the decision summary:** all 17 selected equal-vector queries retained differing path or expectation information; ten excluded events retained ordered frame observations, with missing samples and estimator-channel disagreement preserved.

The successive audits inspected selected, correlated failures. Their number is not independent evidence against Earworm's direction. All masked Experiment 08 cases were rejected; retrieval under masking while withholding an unsupported causal explanation remains unmet.

## Completed work and next authorized action

[PRs #2–#7](https://github.com/trinitron88/earworm/pull/7) have been reviewed and merged; detailed audit links are below. This snapshot starts from main `1cdbb2de5c174ba35e4c77221a0bb171c3f05f3c`.

Brian explicitly authorized [one implementation and run](https://github.com/trinitron88/earworm/pull/2#issuecomment-5745703250), as a scoped exception to the older saved-data-only limit. Its [preregistration receipt](https://github.com/trinitron88/earworm/pull/2#issuecomment-5745907889) preceded the single held-out evaluation. Actual held-out execution revision: `4c9a87756f15fc1f458a3ffae9cd640661a637b3`; the final publication commit is separately reported in the PR receipt.

**Current action:** publish the complete prediction snapshot and branch-B receipt, then stop awaiting review. Retain the simpler frozen prediction reference for the capability demonstrated. No next experiment or automatic audit is authorized.

The estimator-channel provenance audit remains **unstarted and deferred** under [the superseding decision-before-assignment policy](https://github.com/trinitron88/earworm/pull/2#issuecomment-5745619992). It is not a prerequisite.

## Working process and limits

The existing local worker checks every 30 minutes, tracks processed instructions and exits if another worker is active. PR #2 remains the instruction channel; successor PRs carry complete snapshots. Each PR updates this overview. The separate reviewer is unchanged. The worker may push authorized work but does not merge, force-push or change main.

Substantive assignments must name a decision, different concrete actions for plausible results and a bounded stop condition. A report's recommendation does not authorize further work. All frozen Experiment 08 code, models, thresholds, stimuli, results and prior audits remain preserved. New experiments, extraction, training, deployment or spending beyond the completed exception require explicit authorization. Human judgments remain a separate pilot.

## Detailed evidence

| Topic | Record |
|---|---|
| New history-dependent prediction | [Report](experiments/history-prediction-v1/REPORT.md), [protocol](experiments/history-prediction-v1/protocol.json), [group results](experiments/history-prediction-v1/results/heldout/groups.csv), [validity checks](experiments/history-prediction-v1/validation/heldout.json) |
| Experiment 08 | [Milestone](outputs/experiment08-milestone.md), [full report](outputs/competing-accounts-report.html) |
| Calibration and rejection | [Calibration audit](review/experiment08/calibration-audit/completion-20260919/REPORT.md) |
| Four source/impostor comparisons | [Matched-pair audit](review/experiment08/matched-pair-audit-e05-e21/REPORT.md) |
| Feature equality prevalence | [Held-out census](review/experiment08/heldout-feature-prevalence/REPORT.md) |
| Relationships beyond support vectors | [Saved-alignment audit](review/experiment08/equal-vector-alignment-audit/REPORT.md) |
| Ordered frames inside excluded events | [Saved-frame inspection](review/experiment08/excluded-event-frame-timelines/REPORT.md) |

## Historical provenance

[Original handoff notes](review/experiment08/original-snapshot-PROJECT_STATE.md) are preserved byte-for-byte. The original Experiment 08 run had no recorded execution Git revision; source hashes identify its implementation. Initial `SHA256SUMS` and `REVIEW_SNAPSHOT_MANIFEST.json` describe snapshot `06fe4470d64b0a1c00f3e65b7701a393af9a43d8`, not the evolving overview. Later packages carry their own integrity records. Documented reproduction commands are not authorization for another worker run.
