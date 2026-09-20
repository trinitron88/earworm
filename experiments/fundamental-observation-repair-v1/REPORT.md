# Fundamental observation repair: passes the bounded supplied-note test

**Result A.** On 24 fresh held-out phrase groups, replacing only the acoustic observation adapter raises joint-change prediction from 36/48 to 48/48, with the PR #8 primary retrieval code and parameters unchanged. Gain: 0.25, paired group-bootstrap 95% interval [0.083333, 0.416667]. All preregistered adoption and octave-safety gates pass. Adoption is limited to this controlled supplied-boundary task; the next boundary-removal stage requires a separate PM assignment after review.

## What changed

The historical adapter estimates pitch from the strongest spectral peak. The new waveform-only adapter finds local peaks of the normalized square-difference/NSDF periodicity function, selects the earliest peak exceeding a development-selected threshold, and interpolates its lag. The finite grid was 0.85, 0.90, 0.95; development selected **0.85**. The estimator searches 80–2000 Hz, fixed before development, and retains the original spectral estimate, all candidate periods, selected periodicity, availability and uncertainty. It does not blindly divide pitch by two.

The exact PR #8 relative-retrieval reference has the same order 3, cutoff 0.1, prior, temperature 0.05, width 0.08 and smoothing 0.001 on both sides. Calibration fits nothing. For both adapters, the same streams also feed marginal, recency, transition orders 1–3 and full order-3 absolute retrieval. The repair does not claim superiority over these other capable simple mechanisms.

## Design and frozen evidence

Forty fresh groups: 8 development, 8 calibration, 24 held out. New normalized cues descend then rise; previous studies used different normalized cue families. All variants of each group stay together. Each pair has identical actual byte multisets, duration, energy and pitch inventories and identical current cue; only the cue–successor binding differs. Four cells vary timbre/envelope, duration, both or neither. Supplied note boundaries and silent separators remain artificial supports.

Direction, register and overtone dominance are crossed in an eight-run fractional-factorial block in every split. Presentation order is balanced but aliases their three-way interaction. Pure versus fundamental-dominant subtype aliases the direction/register interaction within the non-overtone half; loudness varies by eight-group block, not independently within each training split. These limitations are declared before evaluation. Binding labels always share nuisance factors. Evaluation has six pure, six fundamental-dominant and twelve overtone-family groups, each with new rendering tuples, including longer unseen durations. No evaluation group was replaced or retested.

| Primary acoustic pipeline | Matched | Timbre change | Duration change | Both changes |
|---|---:|---:|---:|---:|
| Old observations + frozen retrieval | 48/48 | 36/48 | 48/48 | 36/48 |
| Repaired observations + same retrieval | 48/48 | 48/48 | 48/48 | 48/48 |

Repaired paired success is 24/24 groups in every cell. All three familywise changed-minus-matched lower bounds are zero. Joint advantage over repaired present-only has lower95 bound 0.75. Joint log loss falls from 2.705680 to 0.000980481; Brier falls from 0.499500980 to 0.000000980.

Full baseline results, both-members success, proper scores and intervals are in `results/heldout/summary.csv`. In the joint cell, repaired absolute retrieval and transitions of order 2/3 also achieve 48/48. Repaired marginal achieves 8/48; recency and order-1 transitions achieve 24/48. With old observations, absolute retrieval and transitions of order 2/3 achieve 26/48. This supports a localized observation repair, not a new relational architecture.

## Safety and causal controls

The predefined pure/fundamental-dominant safety set contains 12 held-out groups. Across their pitched arrived prefix blocks, repaired estimates are within 0.35 semitones in 100%, with zero measured ±12-semitone errors and no prediction accuracy loss versus the old adapter. Pure and fundamental subfamilies are reported separately. All held-out pitched observations are available and within tolerance; mean absolute repaired error is 0.004079 semitones. The old spectral estimator is more numerically precise on simple tones, but has a 19.33% group-weighted octave-error rate across the full mixed observation set. Repeated blocks are not independent observations: summaries and resampling use phrase groups.

For repaired primary retrieval:

- Reset/removal: 8/48 correct, zero paired success, paired probability total variation zero.
- Swap: 48/48 correct, counterpart distribution discrepancy zero.
- Whole-chunk shuffle: zero accuracy loss.
- Ambiguous histories: combined target mass at least 0.99904, each alternative within 0.00048 of 0.5, maximum class probability 0.49952.

The common probability representation maps interval distributions to absolute integer semitone bins relative to A220, spanning -48 through 72, plus an unknown prediction bin. A missing anchor cannot become a correct known-pitch outcome. Known out-of-range targets have zero modeled mass, producing positive-infinite log loss. No clipping is used. `+Infinity` is a valid explicit JSON sentinel. Six pre-freeze scorer tests cover zero target probability, missing anchor, range overflow, ambiguity, octave shifts and serialization. These changes apply only to the new harness; PR #9 remains unchanged.

## Validation and interpretation limits

- Held-out execution revision: `dd4fbea06485bd00117e9340a83a8844859869c5`, distinct from final publication. Frozen inputs match it; only the preregistration receipt was untracked when evaluation started.
- 277 prior artifacts unchanged; primary reference source/config are byte-identical to the historical copies.
- One acoustic pass per split: 720 streams plus 160 future-substitution probes = 880 total; 14 prefix blocks, capacity 32, zero eviction. Local only, no spending or new dependencies.
- Held out: 8,352 hash-chain records, 6,048 independently reconstructed forecast distributions, 96 future-invariance checks. Separate standard-library score reconstruction agrees within 2.23e-16. Saved result files reproduce byte-identically in the recorded environment.
- Forecasts were flushed/fsynced before future reveal/extraction; only arrived bytes entered the worker. Candidate fundamentals come from waveform samples, not generator labels. Diagnostic truth stays outside the predictor. Processing timestamps are not claims of real-time playback latency.
- Python audit-hook process isolation is instrumented, not an adversarial OS sandbox. Pitched-block availability is empirical on these clean synthetic tones, not evidence of calibrated abstention under arbitrary noise or polyphony.
- Bootstrap: 5,000 paired group resamples, seed 2026092020, inverted-CDF quantiles, Bonferroni familywise intervals for three contrasts. Small, constructed subfamilies limit generalization; perfect synthetic counts do not establish reliability on music in the wild.
- The eight-group exploratory calibration result retains a gain interval touching zero; it is not the frozen 24-group adoption decision. No calibration-based retuning occurred.

## Reproduce saved evidence

From this directory in the recorded Python/NumPy environment:

```sh
python scoring.py
python verify.py heldout
python analyze.py heldout
python validation/independent_scores.py
```

These checks use saved outputs without another acoustic pass. `run.py` refuses already-started splits. Recipes/hashes, caches, logs, grids/configs, source snapshots, protocol, preregistration receipt, group observations/results, resource ledger, provenance and checksums accompany this report.

After review, retain the repaired adapter as a new version alongside the historical reference. The PM may then assign a bounded continuous isolated-voice boundary test. No boundary study, natural-performance run, estimator audit or other follow-on is started by this snapshot.
