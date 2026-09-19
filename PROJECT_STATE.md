# Project Earworm — current state

Updated September 19, 2026. This living overview is refreshed in every PR; detailed experimental records and prior audit packages remain historical evidence.

## Goal

Build auditory representation and memory that help AI systems hear, listen to, and interpret music: retain what arrived, remember earlier sound, recognize relationships through changes, and distinguish observations from expectations. Richer musical response is the long-term ambition; the current work does not establish human-like appreciation or subjective experience.

The working architecture separates acoustic descriptions, a representation that changes over time, relationships such as repetition and transformation, and downstream interpretation. Emotion or identity labels should not define what the underlying auditory memory can retain.

## Current phase

**Experiment 08 is complete. We are diagnosing its limitations using saved evidence.** The prototype stores explicit acoustic memories of controlled synthetic monophonic phrases, aligns a heard phrase against candidates, and either retrieves a memory or withholds acceptance. It considers competing explanations for alterations.

MERT remains frozen and was unused in Experiment 08 and the subsequent audits. No Experiment 09 has started. Human judgments remain a separate pilot.

## Main findings

- **Ranking is stronger than accepted retrieval.** The correct phrase ranks uniquely first in 553/576 held-out queries, but the frozen rule retrieves it in only 164/576. The earlier reader accepted 198/576, so Experiment 08 is not a retrieval improvement. Both recorded zero absent-source false acceptances in this set.
- **Calibration is fragile.** A saved-data audit found that omitting the sole six-event calibration group changes the diagnostic threshold and increases errors on that omitted group. The operational model and threshold remain unchanged.
- **Some distinctions disappear in the support features.** Across 576 queries from 16 groups, 17 queries have all twelve support features equal to their strongest absent-history candidates; another 104 differ only in cost and timing loss. All exact tied maxima were retained: 632 pairs, not 632 independent queries.
- **This is only part of the bottleneck.** Those 121 queries span 9/16 groups and accompany 117/412 rejections; 295 rejections have other feature differences. Equal support vectors do not imply equal original sound, equal full alignment evidence, or human perceptual identity.
- **The richer saved state retains distinctions that the support vector omits.** A follow-up inspection of all 17 all-equal queries and their 68 maximum pairs finds different saved transformations or missing-event accounts in every pair. Fifteen queries have only two eligible events. Ten merged-event queries retain a broad-pitch event in the cache that is excluded from matching.
- **Ordered observations also survive inside the excluded events.** All ten inspected events contain earlier/later frequency structure across 380 saved frames. Forty pitch samples are missing, and two examples show disagreement between cached pitch and spectral peak. The observations are separate from memory expectations; no improved retrieval or verified fundamental frequency is established.

All masked cases were rejected. Successful retrieval under masking while withholding an unsupported causal explanation therefore remains unmet.

## Completed work and next authorized step

The [calibration audit (PR #2)](https://github.com/trinitron88/earworm/pull/2), [four-query matched-pair audit (PR #3)](https://github.com/trinitron88/earworm/pull/3), [held-out prevalence census (PR #4)](https://github.com/trinitron88/earworm/pull/4), [living-overview update (PR #5)](https://github.com/trinitron88/earworm/pull/5), and [saved-alignment audit (PR #6)](https://github.com/trinitron88/earworm/pull/6) have been reviewed and merged. This snapshot starts from main `a818d59f86cd8540399ea49f743d2d1bb0fb2736`.

**Completed in this snapshot, awaiting review:** [the saved-frame timeline inspection](review/experiment08/excluded-event-frame-timelines/REPORT.md), assignment `earworm-excluded-event-frame-timelines-v1` ([authorization](https://github.com/trinitron88/earworm/pull/2#issuecomment-5744920500)). All ten fixed event bounds and 380 in-bound frames are accounted for, with original dtypes and missing values preserved. The 300 interior frames are marked as context. A separate table preserves 130 memory-conditioned expectation rows. No agreement score, memory winner, boundary change or revised retrieval decision was produced.

**One proposed next step, not executed or yet authorized:** inspect the frozen estimator implementation and existing channel/flag values to explain the provenance of the pitch-versus-spectral-peak disagreements in two of these events. No extractor rerun, pitch correction, scoring or decision change is proposed. The next authorized worker action is to publish this completed snapshot and await review; the worker stops afterward.

## Working process and boundaries

A local worker checks instructions every 30 minutes, tracks completed work, and exits if another worker is active. PR #2 remains the instruction channel after its merge; successor PRs carry review snapshots. The separate event-triggered reviewer reviews exact commits, may merge accepted work under Brian's delegation, and issues bounded assignments. The worker may push authorized changes but does not merge.

Current work uses saved data and the existing local setup. Original experiment code, protocols, model, operational threshold and results remain frozen. New experiments, training, audio regeneration, spending and broader scientific changes require separate authorization. A report's proposed follow-up is not automatically an execution instruction.

The evidence consists of correlated synthetic variants with supplied two-second windows, a monophonic detector and fixed-capacity memory. It does not demonstrate natural or polyphonic listening, learned memory decay, or human musical identity. Generator metadata stays outside predictor inputs. A quiet location under an alignment does not prove that a performer omitted a note.

## Detailed evidence

| Topic | Record |
|---|---|
| Experiment 08 and causal-memory controls | [Milestone](outputs/experiment08-milestone.md), [full report](outputs/competing-accounts-report.html) |
| Frozen rules and decisions | [Protocol](work/accounts_results/protocol.json), [configuration](work/accounts_results/frozen_config.json), [primary trials](review/experiment08/primary_trials.csv) |
| Calibration and rejection margins | [Calibration audit](review/experiment08/calibration-audit/completion-20260919/REPORT.md) |
| Four source/impostor comparisons | [Matched-pair audit](review/experiment08/matched-pair-audit-e05-e21/REPORT.md) |
| Prevalence, ties and verification | [Held-out census](review/experiment08/heldout-feature-prevalence/REPORT.md) |
| Relationships retained beyond equal support vectors | [Saved-alignment audit](review/experiment08/equal-vector-alignment-audit/REPORT.md) |
| Ordered frames inside excluded events | [Saved-frame inspection](review/experiment08/excluded-event-frame-timelines/REPORT.md) |

## Reproduction

The [original handoff notes](review/experiment08/original-snapshot-PROJECT_STATE.md) are preserved byte-for-byte, including provenance, paths, reproduction commands and limitations. Their workflow status describes the original snapshot and is superseded by this overview. Commands there are documentation, not authorization to rerun an experiment; later audit reports provide saved-data-only verification instructions.

The original run had no recorded execution Git revision. Publication commits identify later snapshots; frozen source hashes identify the recorded implementation. Original `SHA256SUMS` and `REVIEW_SNAPSHOT_MANIFEST.json` describe the initial package, including its old overview and README. Verify that historical package at `06fe4470d64b0a1c00f3e65b7701a393af9a43d8`; those manifests have not been rewritten for this evolving repository. Each later audit has its own integrity records.
