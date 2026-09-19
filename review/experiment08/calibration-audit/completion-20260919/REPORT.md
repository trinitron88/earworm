# Experiment 08: completed saved-evidence calibration audit

**Status: the original margin audit is complete; frozen results are unchanged.**

The original worker found the saved development and held-out pair tables locally. This completes the authorized audit from [PM comment 5740577316](https://github.com/trinitron88/earworm/pull/2#issuecomment-5740577316), reconciling reviews [5255130712](https://github.com/trinitron88/earworm/pull/2#pullrequestreview-5255130712) and [5255192711](https://github.com/trinitron88/earworm/pull/2#pullrequestreview-5255192711) against parent snapshot `b8b6e85ab184d8e243b1e40b7aea6500a31ac105`. The earlier blocker was accurate for that published tree. Its report, scripts, tables, and checkpoint remain unchanged as historical evidence; this completion package supersedes its missing-input status.

The main finding is a mismatch between useful ranking and the frozen support boundary, with both an explicit length pattern in the saved readout arithmetic and sensitivity to the sole six-event calibration group. **This does not show that lowering the threshold is safe.**

## What was read and calculated

The compact export contains 696 queries (120 calibration, 576 held-out) and 6,960 candidate pairs. It retains all ten candidates in the union of each ordinary source-present and source-absent history, their original evidence features, and evaluator-only metadata/history membership. It omits fit queries and the twin used only in the separate ambiguity test. Each history contains one reference and eight distractors after the existing 16-second delay.

The original pair tables store **features, not precomputed support logits**. This audit applies exactly the frozen standardized dot product and intercept to those saved features. Only `available` and the feature vector enter that arithmetic. Group, family, length, source, and history metadata are used for evaluation/stratification, not predictor inputs. No audio extraction, alignment search, fitting, regenerated stimuli, replay, or MERT inference ran. This is a saved-data diagnostic, not Experiment 09.

`input_identifiers.json` records the original local input hashes, the compact export hash, and the original frozen source/protocol hashes. The pair-file hashes were captured now and identify the saved inputs used; they are not retrospective claims of pre-run hash commitments. The original execution Git revision remains unavailable. Publication commits identify snapshots only.

Verification reproduced every one of the 576 saved source-present and source-absent decisions, all archived per-family ranking counts, and the exact frozen calibration threshold and counts. The selected threshold remains **3.6264131202365606**. No alternative diagnostic threshold is installed.

## Ranking and acceptance

There are **553/576 uniquely correct first rankings**, **164/576 correct singleton acceptances**, and **0/576 observed source-absent false acceptances**. Thus 389 uniquely correct first-ranked memories are rejected. The earlier 156/576 accepted-plus-strict-edit-recovery total is unchanged and was not recalculated here; this audit evaluates support and retrieval, not alignment correspondence accuracy.

The margin below is the true-source support logit minus the frozen threshold. The absent margin uses the maximum score among all candidates in the corresponding source-absent history, including the other reference. That other reference is not necessarily in the source-present ranking; the two comparisons must not be conflated.

| Phrase length | Groups / queries | Uniquely correct first | Accepted correct | Median true margin | Closest absent margin |
|---|---:|---:|---:|---:|---:|
| 4 | 4 / 144 | 124 | 32 | -0.381259 | -0.125988 |
| 6 | 4 / 144 | 143 | 68 | -0.208368 | -0.000001276 |
| 8 | 4 / 144 | 142 | 32 | -0.270285 | -0.114039 |
| 10 | 4 / 144 | 144 | 32 | -0.413516 | -0.288481 |

Overall, the median true margin is -0.352650. The median true-minus-maximum-absent score is +4.216742, but it is only +0.000498 for length four; favorable overall separation conceals difficult subgroups. All per-length, per-family, length-by-family, and per-group distributions (minimum, quartiles, median, maximum) are in `results/stratified_margins.json`; individual observations are in `results/query_margins.csv`.

Variants within a phrase group are correlated. These counts and quantiles describe the saved sample, not hundreds of independent replications or population error guarantees.

## A length pattern visible in the fixed arithmetic

For the eight held-out delete-with-rest queries at each length, the saved true-source feature vectors give identical scores within that length:

| Reference events | True-source score | Margin | Accepted / 8 |
|---|---:|---:|---:|
| 4 | 3.5004254872 | -0.1259876330 | 0 |
| 6 | 3.6266266302 | +0.0002135100 | 8 |
| 8 | 3.5126056913 | -0.1138074289 | 0 |
| 10 | 3.3381163839 | -0.2882967363 | 0 |

For this particular saved family, matched-count and coverage contributions improve as length grows, while the frozen coefficients on reference/query log counts contribute progressively less. Their sum peaks at six among the four tested lengths. This explains the arithmetic of this family's length-specific acceptance without changing features or weights. `results/feature_contributions.csv` records the actual additive terms for all available true-source vectors, grouped by length/family/split. Complementary coverage/missing features are redundant, so individual coefficients must not be read as independent causal effects.

This is a narrower conclusion than assigning all failures to phrase length. It does not establish why the fit learned these weights, whether another representation or calibration design would generalize, or whether all other families share the same mechanism.

## Leave-one-calibration-group-out sensitivity

The fitted coefficients and scaler stay fixed. For each diagnostic fold, select a threshold using only the other three calibration groups, with the original candidate levels, at-most-5% empirical false-acceptance constraint, and tie-breaks. Then evaluate the omitted calibration group. The 576 held-out queries do not choose or validate a replacement threshold in this procedure.

| Omitted calibration group (length) | Diagnostic threshold | Retained correct / 90 | Retained false accepts / 90 | Omitted correct / 30 | Omitted false accepts / 30 |
|---|---:|---:|---:|---:|---:|
| e04 (4) | 3.6264131202 | 29 | 1 | 8 | 0 |
| e05 (6) | 3.5126056913 | 28 | 0 | 8 | 6 |
| e06 (8) | 3.6264131202 | 29 | 1 | 8 | 0 |
| e07 (10) | 3.6264131202 | 29 | 1 | 8 | 0 |

The full calibration reproduces **37/120 correct singletons and 1/120 false acceptances**. Only omitting e05 changes the selected threshold: a decrease of 0.1138074289. On that omitted group, false acceptances rise from **1/30 at the frozen threshold to 6/30**; correct singleton retrieval falls from **13/30 to 8/30**, because additional accepted distractors can destroy singleton correctness.

Each calibration length has only one group. Leaving e05 out therefore removes both that group and all six-event calibration phrases. These observations expose sensitivity but cannot separate group-specific acoustics/patterns from length coverage. No four-fold result here supports changing the operational threshold.

## Near-boundary cases limit the zero-error interpretation

- The frozen threshold exactly equals the true-source score for calibration query `e05_query_b_delete_closed`. Its highest-scoring absent-history candidate, `e05_distractor_1`, is only **1.1818279688e-10 below** that threshold.
- For `e05_query_a_delete_closed`, the absent-history maximum lies **1.0221174307e-7 above** the threshold: the recorded calibration false acceptance is real.
- In held-out data, the closest absent-history score is `e21_query_a_delete_closed` / `e21_distractor_3`, **1.2761520001e-6 below** the threshold.
- Two accepted held-out delete-closed true sources lie only **9.1615603992e-11 above** the threshold.

These small margins are measured score differences, not demonstrated floating-point bugs. An independent scalar sum agreed with the unchanged NumPy score arithmetic within 1e-12. Nevertheless, zero observed held-out false acceptances is compatible with an extremely narrow boundary; it does not establish robustness to acoustic variation, different computation, or new groups.

## One bounded proposed next action

Perform a read-only matched-pair inspection of the saved true-source and closest-impostor alignment/evidence for **e05 and e21 delete-closed queries**, accounting for which retained acoustic differences produce these tiny support gaps. Publish the comparison before proposing any threshold or representation change. This recommendation is not executed or separately authorized by this report.

## Reproduce this audit without an experiment run

Use the repository's existing NumPy environment. From the repository root, choose a fresh empty output directory:

```sh
python -B review/experiment08/calibration-audit/completion-20260919/analyze_saved_evidence.py --root . --out /tmp/earworm-margin-check-UNIQUE
```

Compare its six output files byte-for-byte with `results/`. The script verifies the compact input hash, frozen source/configuration identities, evaluator metadata/history membership, all original primary decisions, per-family ranking totals, and the full-calibration selection. The export script documents how the compact input was selected from the worker's saved originals; those two large original pair tables remain unuploaded. `validation.json` records a clean re-execution of this audit and comparison against the original pure threshold-selection routine. `CHECKSUMS.sha256` covers this completion package.

The original experiment sources, frozen settings, results, protocols, and earlier blocker package are preserved. Human perceptual identity and subjective hearing remain untested. No new spending, experiment, reviewer change, merge, or main-branch update is part of this handoff. The worker checkpoints as awaiting review after this one complete publication.
