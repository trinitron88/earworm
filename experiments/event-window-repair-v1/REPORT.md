# Event-window repair: better measurements, adoption withheld

**Branch B.** Trimming 16 ms from each end of each completed inferred event improved group-weighted pitch accuracy from 0.727647 to 0.969580 and removed observed octave errors (0.094954 to 0). Joint reference prediction improved from 14/48 to 45/48. This is evidence that causal support selection helps on these controlled streams. It does not establish that window contamination is the sole cause of remaining failures or that the prototype is ready to adopt.

## Frozen comparison

Forty fresh normalized phrase groups, 8 development / 8 calibration / 24 held out, exclude prior four-study identities. All variants remain in one split. Development considered exactly five symmetric trims (8,12,16,20,24 ms), maximizing event pitch accuracy, then intact reference accuracy, then smaller trim, subject to availability >=.80. It selected trim16. Calibration made no policy or probability changes. Protocol, implementation, configuration and splits were committed before preregistration; evaluation ran once afterward.

The b2 event formation, 64 ms arrival, 32 ms / 4 ms frames, NSDF estimator and reference retrieval/probabilities remain frozen. New measurements use contiguous support inside inferred bounds, >=32 ms and >=4 candidate-pitch cycles. Insufficient support stays unavailable. Full PCM, original observations, candidate uncertainty, original spectral evidence and whole-event duration/bounds are separately retained. Support references and actual computation timestamps are appended. The worker receives only arrived PCM; true boundaries belong only to the evaluator ceiling.

| Cell | Repaired | Whole span | Fixed window | Oracle boundary | Repaired pairs |
|---|---:|---:|---:|---:|---:|
| detached | 45/48 | 36/48 | 12/48 | 48/48 | 21/24 |
| legato | 44/48 | 19/48 | 11/48 | 48/48 | 20/24 |
| duration | 45/48 | 13/48 | 10/48 | 48/48 | 21/24 |
| joint | 45/48 | 14/48 | 10/48 | 48/48 | 21/24 |

These are primary reference predictions, not identity judgments. Both-members success exceeds .80 in every cell, but that alone is insufficient. Every front's seven baselines and all controls, group metrics and proper scores are in [summary.csv](results/heldout/summary.csv), [groups.csv](results/heldout/groups.csv) and [trials.csv](results/heldout/trials.csv); no claim of relational superiority is made.

## Adoption gates and failures

- Oracle ceiling: 48/48 and 24/24 pairs in all four cells, passes.
- Noninferiority fails: familywise lower bounds for repaired-minus-oracle are -.166667 (detached), -.187500 (legato), -.166667 (duration), -.166667 (joint), below -.10. These are 5,000 equal-group paired resamples, seed 2026092050, inverted-CDF quantiles .00625/.99375.
- Joint gain over whole span is .645833, ordinary 95% CI [.500000,.770833]; over present-only lower bound .562500. Both improvement gates pass.
- Joint log-loss increase versus oracle .081733 passes <=.10; Brier increase .046885 fails <=.02.
- Event F1 .968510, pitch accuracy .969580, split .001777, merge .014777, octave error 0: event gates pass. Pitch availability .970001; unavailable/missing events count as pitch failures. Mean available pitch error .001922 semitones.
- Reset/removal: accuracy 11/48, zero both-members success, paired forecast TV 0; pass. Swap: 21/24 paired successes with exact counterpart distributions; pass. Whole-motif shuffle accuracy drop 0; pass.
- Ambiguity fails in groups ewr-23, ewr-26, ewr-27, ewr-35. Two groups put roughly .99902 on one alternative; one is too imbalanced and one assigns only .74929 total to the intended alternatives. Preserving alternatives remains necessary even with improved pitch measurements. These results do not justify silently replacing uncertain evidence with expectations.
- Safety family losses versus oracle: pure 0 (6 groups), fundamental .166667 (6 groups, fails <=.10), overtone .052083 (12 groups). No family removed or threshold weakened.

## Support, time and resources

Across 4,328 retained pitched-event records in heldout forecasts, 137 new measurements were unavailable. Equal-group mean support duration (zero for absent support) was 68.014 ms. Maximum elapsed time from original observation timestamp to appended support observation was 1.353 ms; it includes sequential work, not isolated crop CPU time. Full details: [support trials](results/heldout/support_trials.csv), [support groups](results/heldout/support_groups.csv).

Maximum arrived-audio latency from matched true event end was119.375 ms (inferred end104 ms), under160 ms. This sample-clock delay is separate from measured dispatch/computation clocks, recorded in [resources](results/heldout/resources.json) and the append-only logs. Derived support was never backdated. Maximum observed chunk dispatch-response time was 2.368 ms.

880 total streams (720 episodes plus160 future probes); 14,971 support observation calls including all development candidates. Acoustic split wall time totals 37.668 seconds. The approval-service interruption occurred before preregistration; no heldout or training repetition occurred during it. Conservative active wall accounting is in [provenance](provenance.json), excluding blocked waiting. Storage remains below2 GiB. Heldout maximum23 chunks /1.472 seconds,94,208 raw bytes and308,892 bytes serialized listener payload; development's multiple candidates are counted together. These are serialization/raw-buffer measures, not heap/RSS measurements. Evaluator archives are inaccessible to the worker. There is no eviction or long-term-retention claim.

## Evidence and reproduction

Saved-only validation passed22,268 chained records,12,096 forecasts (maximum reconstruction error2.22e-16),96 future-invariance checks, causal timestamps/control byte semantics, full original/support provenance and446 historical file hashes. Independent standard-library score arithmetic reproduced12,096 scores within4.44e-16, under the preregistered1e-12 tolerance. Hash comparisons remain exact. [Validation](validation/heldout.json), [independent scores](validation/independent_scores.json), [decision](results/heldout/decision.json), [safety](results/heldout/safety.json), [controls](results/heldout/controls.json).

To validate saved evidence using Python3.12 and NumPy2.5.3 from the repository root:

```sh
python experiments/event-window-repair-v1/verify.py heldout
python experiments/event-window-repair-v1/validation/independent_scores.py
```

`analyze.py heldout` reproduces saved tables using no audio calls. Do not rerun `run.py`: split STARTED guards intentionally prevent repeated acoustic execution. Per-split execution-source snapshots, waveform archives, recipes, hashes and preregistration receipt are included. Execution revision: `5bb5cd23d2ed55144dde7a84dc5f4bbd4500ff00`; publication head is separately identified by the PR and completion receipt.

## Limits and stop

Synthetic monophonic material, phase-reset joins, long separators, narrow motif design and fractional factor aliases limit transfer. The family design aliases order with a three-way interaction, pure/fundamental subtype with direction/register, and pitch direction with renderer direction. All baseline comparisons use the same streams. No human perceptual identity, music appreciation, polyphonic listening or long-term memory result follows from generator rules.

Do not adopt this policy or advance musical complexity. Publish this complete evidence snapshot and await review. The PM may choose a further localized approach only through a new explicit bounded assignment with a discriminating decision. No next experiment is started here.
