# Controlled motif robustness: observation prerequisite exposed

**Decision C.** Neither the unchanged PR #8 retrieval reference nor the one allowed readout reparameterization passes the frozen robustness criteria. The evaluator-only fundamental-pitch diagnostic passes, supporting a targeted observation repair before removing supplied note boundaries. This invocation ends at review; it does not implement that repair.

The selected simple retrieval mechanism remains the reference. Its relative matching often survives rendering changes, but its acoustic pitch anchor can be an octave wrong. This is evidence about synthetic fundamental-frequency prediction, not human melodic identity, musical understanding, or natural-performance listening.

## Frozen evaluation

40 fresh motif groups: 8 development, 8 calibration, 24 held out. Each contains paired histories with swapped cue–successor bindings. Actual byte multisets, durations, energy, pitch inventories and current cue are identical within pairs. Two silent separator blocks before the current cue prevent accidental suffix matches; boundaries are supplied. No metadata reaches the predictor.

Four rendering cells: matched; timbre/envelope change; duration change; both changes. Every group has a distinct normalized cue-pair/continuation tuple and render tuple. New cues end below their start, unlike the preceding study's upward cues. Previous E08 six-event phrase identities are not reused. Evaluation durations and rich-demo/simple-cue combinations were withheld. Training rich-family/direction confounding is explicitly documented in the protocol; evaluation crosses both directions with rich/moderate families, six groups each. This is a deliberately constructed distribution, not a random sample of musical instruments.

The adapter, gating, context structure and retrieval code are unchanged. Development chose cutoff 0.1; calibration selected smoothing 0.05 for the candidate versus the reference's 0.001. Probability distributions are scored against generator fundamentals relative to each model's **observed** anchor, so octave errors are penalized. No probabilities are clipped. Brier is expected realized categorical squared error; ambiguous outcomes include the 0.5 irreducible term. Point accuracy uses ±0.35 semitones.

| Acoustic mechanism | Matched accuracy | Timbre | Duration | Joint |
|---|---:|---:|---:|---:|
| Present/marginal | 16.7% | 12.5% | 16.7% | 12.5% |
| Last match | 50.0% | 29.2% | 50.0% | 29.2% |
| Development-selected order-2 transition | 100% | 54.2% | 100% | 54.2% |
| Order-3 absolute retrieval | 100% | 54.2% | 100% | 54.2% |
| Frozen relative retrieval | 100% | 75.0% | 100% | 75.0% |
| Reparameterized relative retrieval | 100% | 75.0% | 100% | 75.0% |

Reference and candidate both achieve paired success 24/24 groups for matched/duration and 18/24 for timbre/joint. The joint 36/48 correct forecasts fall below the stipulated 80% paired-success requirement. Familywise changed-minus-matched intervals also fail noninferiority for timbre and joint; all intervals, including weak baselines and proper scores, are saved in `results/heldout/summary.csv` and `contrasts.csv`.

Joint log loss: reference 2.705680, candidate 1.764620, present 3.117362. Joint Brier: reference 0.499501, candidate 0.477450, present 0.917567. Smoothing improves these scores but changes no point decisions: candidate-minus-reference accuracy gain 0, paired 95% CI [0,0]. It does not qualify for branch B.

## Controls and diagnostic

Reset and balanced successor removal both yield 12.5% acoustic accuracy, zero paired success and exactly identical paired distributions. Swaps exactly equal the counterpart distributions, but their 75% paired success fails the 80% criterion. Whole-chunk shuffle loses zero accuracy. Acoustic ambiguity calibration fails when the pitch anchor is wrong; this failure is retained, not excused by successful memory lookup.

After all acoustic forecasts were committed, the separate evaluator substituted **arrived-note** fundamentals into the same histories and frozen models. This diagnostic achieved 100% accuracy/paired success in every intact cell for both relative retrieval versions and passed all their control/uncertainty gates. Joint gain over acoustic retrieval: **0.25, paired group-bootstrap 95% CI [0.083333, 0.416667]**. It satisfies the preregistered observation-localization criterion. The oracle is not an acoustic system and contributes no deployable success claim.

The bounded saved anchor/lookup trace records one retrieved entry for each intact joint query. Six groups whose current cue has the overtone-rich rendering have approximately +12-semitone anchor and forecast errors; the others are near zero. The adapter chooses the strongest spectral peak, which is the second harmonic in this subfamily. This supports repairing the observation step, not claiming that memory capacity or matching must be replaced. See `anchor_lookup_diagnostic.json` and the separately labeled oracle records.

## Integrity, resources and limits

- Exact frozen PR #8 code/config copies verified; 199 prior tracked artifacts unchanged.
- One held-out execution at `e5211d4dfd01fb06abbbc452fd55264b0a8bf1e8`, distinct from final publication. Only the preregistration receipt was untracked at evaluation start; frozen inputs matched the commit.
- 720 episode streams plus 160 future-substitution forecast probes = 880 total. No repeated audio evaluation. Maximum 14 prefix blocks, capacity 32, zero eviction. Local only, no spending.
- 8,352 held-out hash-chain log records; 2,592 acoustic forecasts independently reconstructed with maximum probability difference 2.23e-16; 96 held-out future-invariance checks. Another 2,592 oracle outputs were independently reconstructed from saved arrived fundamentals.
- All acoustic forecasts were flushed/fsynced before reveal/extraction. Timestamps describe processing availability, not real-time playback latency. The Python audit guard is instrumented process isolation, not an adversarial OS sandbox.
- Development/calibration score-coordinate correction occurred before evaluation, using saved observations and the same finite grids. Earlier event-log scores are preserved under their original coordinate definition. Final model selection and evaluation use the declared observed-anchor coordinates. The exploratory calibration report describes the models used when those streams ran, not the later calibrated model.
- Accuracy and proper scores weight groups equally. 5,000 paired group resamples, seed 2026092007; three changed-cell contrasts use Bonferroni percentile intervals. Bootstrap claims are limited by 24 constructed groups.
- Clean monophonic blocks, stipulated continuations, supplied boundaries, short history, no eviction, no natural Bach/polyphony and no human judgments. MERT untouched.

## Reproduce saved-evidence checks

With the recorded installed Python/NumPy environment, from this package:

```sh
python verify.py heldout
python analyze.py heldout
python validation/reproduce_diagnostics.py
```

These operate on saved records; they do not rerun acoustic streams. `run.py` refuses an already-started split. `freeze.json`, `preregistration_receipt.json`, `run_ledger.json`, `provenance.json`, recipes, acoustic caches, per-arrival and pre-reveal logs, all trial/group metrics and checksums are included. The new package alone and root `PROJECT_STATE.md` comprise the successor diff.

After review, the PM may assign one bounded observation repair with fresh confirmatory groups. No boundary-removal study, estimator audit or other follow-on is started here.
