# Experiment 08: four saved true-source / impostor comparisons

**The four cases separate near-equal candidate evidence from absolute rejection.** In three comparisons, the true source and strongest impostor differ in only two of twelve support features: aggregate alignment cost and mean timing loss. Both differences come from the same small timing residual imbalance. In the fourth, the true source leads by 4.67 support units but remains just below the global acceptance threshold.

This is the bounded saved-data assignment [earworm-e05-e21-matched-pair-v1](https://github.com/trinitron88/earworm/pull/2#issuecomment-5743879321), following [review 5255281106](https://github.com/trinitron88/earworm/pull/2#pullrequestreview-5255281106). The new work branch starts from main at `f463c0673035bdf4b0b20bdb715d5442b398ddb4`, which contains reviewed audit snapshot `3da31dacd1abda91a37a8a8cb5d9c200335ea3f6`. Every earlier experiment, audit, and blocker artifact is preserved.

## Inputs and method

The four queries are `e05_query_a_delete_closed`, `e05_query_b_delete_closed`, `e21_query_a_delete_closed`, and `e21_query_b_delete_closed`. Group e05 is calibration data; e21 is held-out data inspected post hoc. All four references contain six detected events and their queries contain five. These are selected, correlated diagnostic cases, not a new evaluation sample.

The original development/held-out pair tables supply already saved feature vectors and retained alignment paths. The prior compact export supplies all ten candidates and both nine-member histories for each query. Twelve original cached acoustic descriptions supply typed event measurements and, for the four queries, RMS frames. No audio was read, generated, or re-extracted. No alignment search, parameter fit, training, replay, or MERT inference ran.

All original pair-table hashes match the preceding audit's identifiers. Each selected cached description's full digest matches its original extraction timing record. `input_identifiers.json` records those checks and the new sanitized export's hash. These file hashes identify the saved inputs; they are not new claims of pre-run commitments. Original execution Git provenance remains unavailable.

The frozen score is the same standardized linear sum, with threshold **3.6264131202365606**. Generator metadata routes evaluation only; it is not scored. All four scores and margins reconcile exactly to the completed audit.

## Which candidate competes with the source?

“Impostor” below means the maximum-scoring candidate in the source-absent history, including its alternate reference. We separately search the distractors in the source-present history. **For these four queries, the same candidate wins both searches.** Each maximum is unique under exact score equality and also unique within 1e-9 among the absent-history candidates. The e05-b *true source and impostor*, however, fall within the prior ranking diagnostic's 1e-9 near-tie tolerance. That diagnostic tolerance is not part of operational acceptance.

| Query | Strongest impostor | True score minus impostor | True score minus threshold | Impostor minus threshold | Frozen emitted result with source present |
|---|---|---:|---:|---:|---|
| e05 a | e05_distractor_0 | -4.463635e-7 | -3.441517e-7 | +1.022117e-7 | Wrong singleton: impostor |
| e05 b | e05_distractor_1 | +1.181828e-10 | 0 exactly | -1.181828e-10 | True singleton |
| e21 a | e21_distractor_3 | +8.923636e-7 | -3.837884e-7 | -1.276152e-6 | Reject all |
| e21 b | e21_distractor_1 | +4.671581425 | -8.914791e-7 | -4.671582316 | Reject all |

The e21-b comparison is **not** a near source/impostor tie. Only its absolute source score is near the threshold. The source-absent history accepts the e05-a impostor and rejects all candidates for the other three queries. Exact values, history maxima/ties, and accepted handles are in `results/scores_and_margins.csv` and `results/summary.json`.

## Saved correspondences and the small score gaps

Event indices in the data files and the sequences below are zero-based. A listed reference index sequence corresponds in order to query indices `[0,1,2,3,4]`.

For e05-a, e05-b, and e21-a:

- True-source best path: reference `[0,1,2,4,5]`; reference event **3** is unmatched.
- Impostor best path: reference `[0,1,3,4,5]`; reference event **2** is unmatched.
- Both paths match five events, cover 5/6 of their reference and all query events, have zero mean pitch loss, and have an exact-pitch fraction of one. Their ten non-timing-dependent feature values are identical.
- The largest pitch residual on these best paths is approximately 1.43e-6 semitone for one e05-a impostor correspondence. It lies inside the existing 0.05-semitone loss dead zone; the saved pitch-loss feature is therefore zero. No tolerance was changed.

The paths use the same fitted timing scale within each comparison (approximately 0.775), but different timing offsets and correspondences. The saved residuals produce slightly different mean timing losses. The frozen total cost also contains that timing loss, so the two nonzero feature contributions are **two arithmetic routes for the same timing evidence**, not two independent cues.

| Query | True minus impostor mean timing loss | Contribution through cost | Direct timing contribution | Sum of contributions |
|---|---:|---:|---:|---:|
| e05 a | +9.004739e-5 | -2.619543e-7 | -1.844092e-7 | -4.463635e-7 |
| e05 b | -2.384186e-8 | +6.935765e-11 | +4.882605e-11 | +1.181837e-10 |
| e21 a | -1.800215e-4 | +5.236953e-7 | +3.686683e-7 | +8.923636e-7 |

With five matches and one unmatched reference event, the saved cost difference is 5/6 of the mean-timing-loss difference; the constant gap penalty cancels. For each feature, the additive score-gap term is `coefficient × (true feature − impostor feature) / frozen scale`. The intercept and centering constants cancel. Raw feature differences, scales, coefficients, and all twelve terms are published in `results/feature_gap_contributions.csv`.

The e21-b impostor instead matches four events: reference/query pairs `[[0,0],[2,1],[4,3],[5,4]]`, with unmatched reference indices `[1,3]` and unmatched query index `[2]`. The source still matches five. Its 4.671581425 score advantage is mostly the sum of reference-coverage/missing-fraction contributions (+1.757308544), query-coverage/insertion-fraction contributions (+2.730324675), and matched-count contribution (+0.183067400). Cost and timing add about +0.000880805. Complementary coverage/gap features are redundant; these are bookkeeping contributions, not independent causal effects.

`results/saved_path_summary.csv` includes **all retained paths**, marking path zero as the one used by the support features. `results/saved_correspondences.csv` exposes measured pitch/onset pairs, saved residuals, and dead-zone losses for every retained correspondence. Alternatives were not rescored or newly searched.

## Energy observations stay separate from candidate identity

For each stored path, the audit applies the existing observation rule to the saved query RMS frames: transform the unmatched reference event's onset/offset using that path's saved scale and offset, trim 20 ms from each end, and compare the maximum measured RMS against `max(1e-5, 1% of the query's maximum RMS)`.

The interval is an **alignment hypothesis**. RMS values are measured acoustic evidence. The resulting quiet/unresolved label does not identify a physical cause. For the best paths in the three near-tie cases:

| Query | True-source proposed gap: maximum RMS | Impostor proposed gap: maximum RMS | Quiet threshold |
|---|---:|---:|---:|
| e05 a | 0.019966746, unresolved | 4.256e-9, quiet | 0.001844196 |
| e05 b | 0.022553524, unresolved | 0, quiet | 0.001844196 |
| e21 a | 0.023196541, unresolved | 0, quiet | 0.001846355 |

The true-source gap windows are around 0.558–0.589 s; the impostor windows are around 0.410–0.441 s. They examine different places in the same measured query. A wrong-source alignment can point to a quiet place. These cases therefore do not justify treating quiet-at-a-predicted-location as proof of memory identity or a performed deletion.

For e21-b, the source's proposed window is also unresolved (maximum RMS 0.019887676); both unmatched impostor windows contain substantial energy (0.126741126 and 0.181516454). All retained-path windows, exact bounds, frame counts, maxima, thresholds, and unresolved physical causes appear in `results/missing_position_energy.csv`. These observation labels were calculated now from saved frames using the unchanged rule; they are not represented as previously emitted runtime explanations.

There is **no direct energy feature in the twelve-dimensional frozen support vector**. These energy observations therefore contribute zero additional direct terms to the computed score gaps. This does not mean energy is irrelevant to upstream event detection. `results/measured_events.csv` preserves raw event timing, pitch/quality measures, and query-event RMS summaries for inspection.

## Arithmetic tolerance and limits

Saved residuals, losses, and best-path feature calculations reconstruct exactly in the existing local NumPy environment. The independently summed feature-gap contributions differ from direct subtraction of the two frozen scores by at most **2.079e-15**; scalar score summation differs by at most **1.777e-15**. The e05-b direct gap is 1.1818279688e-10, while summing feature differences gives 1.1818370632e-10. The discrepancy is about 9.1e-16 and does not change the sign.

Verification uses an absolute arithmetic tolerance of 1e-12 only to check equivalent calculations. Maximum-candidate selection and operational `score >= threshold` decisions remain unchanged and exact. The separately reported 1e-9 near-tie list follows the prior ranking diagnostic. Neither tolerance is newly applied to acceptance. Small score differences are not evidence of a floating-point bug or a perceptually meaningful difference. Saved onsets are float32 measurements; stability under a new measurement or computation path was not tested.

Observed: these selected candidates retain different correspondences and timing residuals, while three support-vector pairs agree on all features except two timing-dependent entries. Consequence of fixed arithmetic: those small timing differences determine their scalar ordering; the global threshold separately controls acceptance. Hypotheses about detector resolution, how the fitted weights arose, or whether another representation would generalize remain untested. Four selected synthetic cases cannot establish a causal explanation, a general failure rate, human musical identity, or subjective hearing.

## One bounded proposed next action

Count, using the already saved held-out candidate tables, how often the true source and strongest absent-history candidate agree on all ten non-timing features and differ only in cost/timing loss. Stratify those cases by group and transformation family and report their frozen acceptance outcomes. This would measure whether the three-case pattern is localized or common. It is a proposal only; it has not been executed, and it would not change thresholds or regenerate data.

## Check the package

Use the existing NumPy environment and a new empty output directory:

```sh
python -B review/experiment08/matched-pair-audit-e05-e21/analyze_saved_pairs.py --root . --out /tmp/earworm-pair-check-UNIQUE
```

Compare the eight generated files against `results/`. The script verifies the compact source export and frozen hashes, reproduces maximum/tie membership, reconciles all four previous scores/margins, reconstructs retained residuals/losses, and checks additive contributions. `validation.json` records a clean re-execution and byte-identical outputs. The export script shows exactly which existing inputs were selected; full local pair tables and caches remain unuploaded. `CHECKSUMS.sha256` covers this new package separately.

After one complete successor PR is published, the worker checkpoints as awaiting review and stops. The reviewer may review/merge under its separately delegated authority; this worker does not merge, alter main, or execute this report's proposed follow-up.
