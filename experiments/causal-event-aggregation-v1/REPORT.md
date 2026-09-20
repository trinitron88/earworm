# Causal event aggregation: stop localized measurement repairs

**Branch C: reject the tested aggregator as a streaming front and end the crop/within-event aggregation micro-repair sequence.** The MAP-point path recovered pitched events slightly more often than trim16 but gave identical intact reference prediction scores. The uncertainty-aware mixture regressed: joint accuracy40/48 versus trim16's46/48, paired difference-.125,95% CI[-.250,-.020833]. Oracle-boundary reference remained48/48 throughout.

This is a negative result for the two declared policies and the specific conservative mixture. It does not prove uncertainty-aware retrieval is generally ineffective, that event boundaries alone cause the remaining failures, or that another within-event policy cannot work. The decision to end this repair sequence was a preregistered project gate.

## Design and freeze

Forty fresh normalized groups (8 development,8 calibration,24 held out), excluding189 earlier normalized identities, with all variants in their group. Same controlled detached/legato/duration/joint cells, rendering families and nuisance aliases. Two policies declared before development:32/48 ms or48/64 ms analysis windows, inside frozen b2 completed-event boundaries with8 ms edge inset and8 ms hop. Frozen NSDF extracts each window. Validity requires four pitch cycles; unavailable windows contribute explicit unknown mass. Periodicity weights clusters spanning at most.35 semitone, with no octave folding or expected-pitch snapping. At least two valid windows are required; retain the two largest clusters, with other mass unknown. MAP point requires largest-cluster probability>=.5. Every window candidate, original whole observation and unchanged trim16 record remains available separately from the point interpretation.

Development selected32/48 ms by the frozen lexicographic rule: valid/available>=.80, best group pitch accuracy, best intact MAP Brier, then simpler policy. Pitch accuracy1.0 versus.962682 and Brier.017583 versus.140571. Calibration fitted no parameter: uncertainty scalar remained1 in its declared singleton range. Its exploratory failures were saved without retuning. Heldout ran once after the [preregistration receipt](preregistration_receipt.json), at execution`623cb7012bebb35c699168dc5f0e4beda0750d1c`; publication head is identified separately by the PR/completion receipt.

Two paths use identical measurements. MAP feeds the unchanged seven simple models. The uncertainty path forms product-weighted candidate histories and evaluates the same frozen lookups; at most16 histories survive each step. Unavailable/pruned probability is retained as unresolved output mass, not renormalized into confident alternatives. Integer acoustic anchors map predictions to the unchanged scoring bins. This bounded approximation treats event uncertainties as independent and makes an entire unresolved history contribute unknown output; that conservative choice matters to the result. In heldout, maximum retained history count was8, below the cap. No predictor training or uncertainty fitting occurred.

## Prediction and uncertainty

| Cell | MAP aggregation | Uncertainty mixture | Trim16 | Whole span | Fixed window | Oracle boundary |
|---|---:|---:|---:|---:|---:|---:|
| detached | 46/48 | 42/48 | 46/48 | 38/48 | 13/48 | 48/48 |
| legato | 44/48 | 37/48 | 44/48 | 15/48 | 10/48 | 48/48 |
| duration | 45/48 | 37/48 | 45/48 | 12/48 | 9/48 | 48/48 |
| joint | 46/48 | 40/48 | 46/48 | 11/48 | 9/48 | 48/48 |

The table is transformation-aware reference prediction, not identity judgments. The MAP path and trim16 have equal intact scores here; this is not an equivalence proof. All seven models for each of six front/path combinations, every control, both-members success, proper scores, entropy, unknown mass and confidence are in [summary](results/heldout/summary.csv), [groups](results/heldout/groups.csv) and [trials](results/heldout/trials.csv). Fixed ten-bin reliability is in [calibration bins](results/heldout/calibration_bins.csv); no post-hoc calibration is applied.

Mixture both-members success:21/24 detached,18/24 legato,18/24 duration,20/24 joint. Legato and duration fail the.80 threshold. Familywise selected-minus-oracle lower bounds are-.291667,-.458333,-.458333,-.375, all below-.10. Bootstrap:5,000 paired equal-group resamples, seed2026092060, inverted-CDF quantiles.00625/.99375; ordinary contrasts use.025/.975.

Joint mixture Brier increase versus oracle is.452027, above.02. Log loss is explicitly+Infinity where known outcomes receive zero mass; no clipping hides this. Mean joint reference unknown mass is.346428, versus.000020 for MAP and trim16. The declared product/unknown rule compounds uncertain event evidence; retaining uncertainty alone did not make its downstream use well calibrated. Joint mixture gain over present-only has lower95 bound.5625, but winning that baseline cannot compensate for regression against trim16.

MAP joint Brier increase is.035164, also above.02; thus even the more accurate point path does not establish all required calibration gates.

## Measurements, controls and safety

MAP event F1.971841, pitch accuracy/availability.976945, split0, merge.012159, octave error0. Trim16 pitch accuracy.974210; whole-span.734311. Mean absolute available pitch error is.003633 semitones for aggregation versus.001815 for trim16. The unchanged event front still omits/merges some evidence; the small pitch-availability increase did not improve intact retrieval.

Mixture reset/removal give9/48 and8/48 accuracy, zero paired success and paired TV0; swap gives20/24 pairs with exact counterpart distributions; shuffle improves accuracy by.041667. Those gates pass. Ambiguity fails in15/24 groups for mixture,3/24 for MAP,2/24 for trim16 and0/24 for oracle. Complete alternative masses, deviations and confidence remain in [controls](results/heldout/controls.json).

Mixture rendering-family accuracy losses versus oracle: pure0, fundamental.354167, overtone.197917; the latter two exceed.10. MAP and trim16 both lose.104167 for fundamental and.062500 for overtone, so the point path also narrowly misses the fundamental-family requirement. [Every model's family results](results/heldout/all_model_families.json) and the frozen [primary safety gate](results/heldout/safety.json) keep this distinction visible.

Event and sample-latency gates pass; family safety and improvement over trim16 do not. Under the frozen precedence those failures selectC, not the measurement-candidate branchB. [Decision](results/heldout/decision.json) records all gates. End localized crop/aggregation repairs, retain previous evidence without adoption, and await the PM's next explicit bounded decision about a different event representation or concrete blocker. No next experiment is started.

## Causality, budgets and validation

The listener receives contiguous arrived PCM only. Full captured PCM, original/trim16 evidence, every within-event window's bounds/hash/candidates/periodicity/RMS, computation and availability clocks, and versioned interpretations are separately retained. Forecasts are hash-chained and fsynced before reveal; source metadata and oracle boundaries never enter the operational API. True-boundary ceiling is evaluator-only.

Maximum sample-clock latency from matched true event end157.5 ms; inferred-end104 ms. These are distinct from actual computation clocks: maximum original-to-aggregate elapsed6.666 ms; chunk dispatch-response8.628 ms. Derived observations are not backdated. See [resources](results/heldout/resources.json), [candidate statistics](results/heldout/candidate_groups.csv) and raw saved event/cache records.

880 total streams:720 episodes plus160 future probes.124,558 aggregation-window extractions and8,422 trim16 support extractions, including all development candidates;82.752 seconds acoustic split wall time. Complete work stayed under two hours and retained artifacts under2 GiB. Maximum23 chunks/1.472 seconds,94,208 raw bytes and1,440,628 serialized listener bytes; development's multiple-policy payload reached1,960,418. Serialized accounting includes alternate fronts/window evidence and conservatively duplicates shared MAP/mixture records; it is not heap/RSS. Evaluator archives remain inaccessible. No eviction or long-term-retention test.

Saved-only validation passed22,268 chained records,18,144 reconstructed forecasts,96 future-invariance checks, causal timestamps, paired/control byte semantics,40 fresh identities and540 historical file hashes. Independent scalar aggregation and mixture reconstruction used saved window observations only; maximum probability error3.33e-16. Independent score arithmetic reproduced18,144 scores within4.44e-16. Numerical tolerance1e-12; immutable hashes exact. The only pre-freeze validator correction replaced exact point equality with the already-declared tolerance after a9e-16 summation difference; no acoustic or model rerun.

[Validation](validation/heldout.json), [independent scores](validation/independent_scores.json), [provenance](provenance.json), [checksums](CHECKSUMS.sha256).

Saved-evidence reproduction with Python3.12/NumPy2.5.3, from repository root:

```sh
python experiments/causal-event-aggregation-v1/verify.py heldout
python experiments/causal-event-aggregation-v1/validation/independent_scores.py
python experiments/causal-event-aggregation-v1/validation/saved_diagnostics.py
```

`analyze.py heldout` regenerates saved tables without acoustic extraction. Do not rerun `run.py`; STARTED guards deliberately prevent repeated acoustic execution. Each split's execution source/config snapshot is retained. Numerical scores can vary within the stated tolerance across environments; evidence hashes remain exact.

## Interpretation limits

Synthetic monophonic material has phase-reset joins, long separators, narrow motif families and fractional aliases (order with a three-way interaction, pure/fundamental subtype with direction/register, pitch direction with renderer direction). Forty normalized groups do not imply broad musical diversity. Construction rules and true-note labels do not establish human perceptual identity. No human pilot, music appreciation, polyphony or long-term transformed recognition was evaluated. MERT and all historical packages are unchanged; spending is zero.

Schema note: frozen`comparisons.csv` retains the inherited column name`repaired_minus_oracle`; in this new package its values are **mixture-minus-oracle**, as the frozen analysis implementation specifies. The `repaired` front label elsewhere always denotes unchanged trim16. The inherited boundary-window diagnostic is saved evidence only and does not determine the branch. These labels are documented without rewriting frozen outputs.
