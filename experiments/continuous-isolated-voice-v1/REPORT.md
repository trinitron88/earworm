# Continuous isolated voice: event windows remain a prerequisite

**Result B.** The evaluator-only supplied-boundary ceiling predicts 48/48 continuations in every fresh held-out cell. The operational streaming system receives only fixed 64 ms PCM chunks and does not pass: joint-cell retrieval predicts 8/48, with no successful paired groups. Do not advance musical complexity. After review, the PM may assign one targeted event-window repair on fresh groups; this snapshot does not run it.

The important distinction is between coarse event timing and useful acoustic spans. Streaming event F1 is **0.971803**, yet pitched-event accuracy is **0.674921**. The same frozen pitch estimator reaches 1.0 with the evaluator's true spans. The frozen diagnostic finds 1,255 wrong matched pitch observations, all with inferred bounds differing from true bounds. This localizes a prerequisite at the interaction between event formation and the accepted block estimator; it does not identify a proven repair or show that retrieval or the general research direction failed.

## Operational contract

A synthetic monophonic prefix is rendered continuously and delivered as contiguous 1,024-sample chunks at 16 kHz. No note boundaries, durations, pitches, motif identity, future bytes or metadata reach the worker. Legato has no zero gap at pitch changes, though independent phase resets at joins remain an artificial cue. Long inter-motif silence and trailing evidence silence also remain. This is not a natural-performance claim.

The new front forms events from the accepted frozen NSDF observations on 32 ms windows every 4 ms. Development selected b2: a 1.25-semitone change and two confirmations; a silence/unavailability transition requires eight confirmations. Retrospective boundaries use the first changed frame's midpoint. A segment is observed only once sufficient arrived evidence confirms it. The primary relative retrieval's code, order, cutoff and probability parameters remain exact historical copies. No calibration fitting occurred.

The fixed-window comparator treats completed 64 ms chunks as events. The `oracle-boundary` comparator receives true spans only in the evaluator, after the operational forecast is committed; it is a non-operational ceiling. Every front gives marginal/present, recency, transitions 1–3, absolute retrieval and relative retrieval the same events/history within that front. Trailing unavailable events are trimmed consistently before forecasting. The ceiling is never labeled an acoustic capability.

## Frozen prediction results

Forty new normalized motif groups are split 8/8/24. All variants stay within their group. Exact normalized identities are checked against all three preceding studies' saved recipes before generation. Pair members have identical source-unit byte multisets, durations, energy and sample inventory, and byte-identical current probe/tail. Chunk multisets need not match because chunk edges cut reordered source units; verification checks the actual archived PCM against source-unit hashes. No unit boundaries are supplied operationally.

| Reference retrieval input | Detached | Legato | Duration jitter | Joint |
|---|---:|---:|---:|---:|
| Streaming inferred events | 36/48 | 12/48 | 9/48 | 8/48 |
| Fixed windows | 8/48 | 7/48 | 8/48 | 8/48 |
| Evaluator true boundaries | 48/48 | 48/48 | 48/48 | 48/48 |

Streaming paired success: 13/24, 2/24, 0/24, 0/24 respectively. The required 80% criterion and four-cell noninferiority fail. Joint advantage over streaming present-only has lower95 bound zero. Joint increases over ceiling are 4.626298 in log loss and 0.978874 in Brier, exceeding the frozen limits. All baselines/cells/controls, proper scores and group intervals are retained in `results/heldout/summary.csv`; four streaming-minus-ceiling familywise comparisons are in `comparisons.csv`.

## Event formation, safety and controls

Metrics average trials within each group, then groups equally; repeated events are not independent samples. Time-only greedy IoU matching is followed by a 25 ms onset/end requirement. Missing/unavailable pitched events count against pitch accuracy.

| Event metric | Streaming | Fixed window | True-boundary ceiling |
|---|---:|---:|---:|
| F1 | 0.971803 | 0.150814 | 1.0 |
| Pitched-event accuracy | 0.674921 | 0.722666 | 1.0 |
| Pitch availability | 0.940773 | 0.806818 | 1.0 |
| Octave-error rate | 0.104588 | 0.013655 | 0.0 |
| Mean onset error | 8.52 ms | 20.15 ms | 0 |
| Mean end error | 9.42 ms | 19.78 ms | 0 |

Streaming split and merge rates are 0.002198 and 0.014357. Thus the broad timing gates pass while pitch and safety gates fail. The predefined diagnosis does not require coarse F1 to fail: with ceiling pitch accuracy >=0.95 and streaming <0.95, wrong matched windows must differ from true bounds in >=90% of cases; observed fraction is 100%. This rule was finalized before held-out generation after development showed this distinction. It does not establish whether trimming, delayed refinement or another approach will work.

Reset/removal produce 8/48, zero paired success and exactly identical paired distributions. Swaps exactly match their counterparts but have zero paired successes, failing the prediction requirement. Shuffle does not reduce accuracy. Ambiguity calibration fails: minimum mass on the two expected alternatives is 0.00004. Subfamily safety comparisons also fail. These outcomes are retained independently of the localization decision.

## Causality, storage and integrity

The maximum arrived prefix is **23 chunks / 1.472 seconds**; no complete waveform unit exceeds 2 seconds. The maximum true-end decision latency is 154.125 ms, within the frozen 160 ms bound. Maximum inferred-end delay is 104 ms. Each held-out frame/event records actual computation UTC/monotonic timestamps; these are checked between its containing chunk's dispatch and response. Retrospective boundary times are not feature-availability times. Audio was delivered in a fast broker, not real-time playback, so these are audio-evidence delays plus separately recorded processing times, not a measured real-time service guarantee.

The worker retains its arrived raw prefix, frame cache, event/candidate records, pending boundary state, chunk hashes and immutable config. Raw prefix maximum is 94,208 bytes; the maximum serialized listener payload is 214,284 bytes, including both operational fronts. These are representation counts, not peak Python heap/RSS. All containers are bounded by the chunk/event limits; capacity is 32 events per front and no eviction occurs. The evaluator archive is inaccessible to the guarded worker. **Long-term retention beyond recent-buffer eviction is not tested here.**

- One pass per split: 720 streams plus 160 future probes = 880. No acoustic reruns or paid compute.
- Held-out execution `d50e24a6e0e847b4099a1ac05971dea7a5d6bbba`, distinct from final publication; preregistration precedes generation and frozen inputs match that commit.
- 22,268 held-out hash-chain records, 9,072 forecast distributions independently reconstructed within 2.23e-16, 96 future-invariance probes. Independent standard-library score arithmetic also agrees; saved analyses reproduce in the recorded environment.
- 358 prior artifacts preserved; accepted observation source/config and primary retrieval source/config unchanged. Extra computation-time instrumentation was added before evaluation; original development/calibration source snapshots remain recorded.
- 5,000 paired group bootstrap samples, seed 2026092030; inverted-CDF quantiles; Bonferroni familywise intervals for four cell comparisons. Nonsignificance is not treated as noninferiority.
- Fractional-factorial aliases are explicit in the protocol: order aliases a three-factor interaction, pure/fundamental subtype aliases direction/register, and pitch direction is coupled to renderer direction. Claims are restricted to the constructed cells.
- Operational isolation uses a tested Python audit guard, not an adversarial OS sandbox. No human perceptual identity, polyphony, natural Bach, session continuity or broad musical understanding is inferred.

## Saved-evidence reproduction

From this package in the recorded installed environment:

```sh
python verify.py heldout
python analyze.py heldout
python validation/independent_scores.py
```

No new audio extraction or experiment is needed. `run.py` refuses started splits. Protocol, configs, grids, archived PCM/recipes/hashes, observations, event traces, pre-reveal logs, uncertainty, per-group scores, checksums and provenance accompany the report. Next work requires a separate bounded PM assignment after review.
