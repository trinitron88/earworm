# Identical present sound, different auditory histories

**Decision B: retain transformation-aware sequence retrieval as the prediction reference for this controlled task.** It and the relational readout passed both basic anticipation and the predefined transposition transfer condition, with no measured difference between them. This demonstrates causal prediction using auditory history; it does not demonstrate an advantage beyond retrieval, musical meaning or subjective hearing.

[Authorization](https://github.com/trinitron88/earworm/pull/2#issuecomment-5745703250) · [Published preregistration](https://github.com/trinitron88/earworm/pull/2#issuecomment-5745907889) · [Frozen protocol](protocol.json) · [Machine-readable decision](results/heldout/decision.json) · [Selected reference](selected_reference.json)

## What was predicted

An earlier three-block cue Q was followed by one continuation, and a different cue R by another. The paired history swapped those successors. Both histories contained the same waveform bytes/counts, pitch inventory, duration and block count; only temporal relationships differed. Demonstration order and diagnostic lag were counterbalanced. The final two history blocks and current probe formed Q and were byte-identical within each pair.

The task rule stipulated that Q predicts its earlier observed successor. The predictor received no cue names, generator parameters, group labels, candidate sets or future waveform. It received completed audio blocks through an arrival interface and stored continuous acoustic observations. In the transfer family, the query cue was uniformly transposed by +31 or +36 semitones; the predicted continuation had to move with it. That target pitch had not occurred in the episode or development/calibration data. Its closest training pitch was **5.393 semitones away**, exceeding the frozen .35-semitone tolerance.

All observations came from a new isolated clean-block spectral adapter. This is not a repair or retest of Experiment 08's eligibility gate, support aggregation or calibrated acceptance threshold. Those three mechanisms and all original artifacts remain frozen. MERT was not used or changed.

## Held-out result

There were **24 fresh held-out phrase groups**, each weighted equally. Each intact condition has two paired forecasts per group. Both successful mechanisms achieved **48/48 correct forecasts and 24/24 successful pairs** in basic anticipation and separately in transfer. The other 480 held-out episodes are correlated controls, not additional independent groups.

| Mechanism | Basic accuracy | Basic paired success | Transfer accuracy | Transfer paired success | Transfer log loss |
|---|---:|---:|---:|---:|---:|
| Present/marginal | 14.6% | 0.0% | 14.6% | 0.0% | 1.759884 |
| Last-match recency | 50.0% | 50.0% | 14.6% | 0.0% | 1.803549 |
| Transition (order 2) | 100.0% | 100.0% | 14.6% | 0.0% | 1.759884 |
| Absolute sequence retrieval | 100.0% | 100.0% | 14.6% | 0.0% | 1.759884 |
| Transposition-aware retrieval (order 3) | 100.0% | 100.0% | 100.0% | 100.0% | 0.000980 |
| Relational readout (order 3) | 100.0% | 100.0% | 100.0% | 100.0% | 0.000980 |

Both successful mechanisms have intact Brier error **0.00000098** and mean log loss **0.00098048 nats** in each family. The relational-minus-retrieval transfer accuracy difference is **0.00**, with paired group-bootstrap 95% interval **[0.00, 0.00]**, inside the preregistered ±.05 equivalence margin. Proper scores also agree. The interval is degenerate because every observed group difference is zero; it does not establish universal equivalence outside this task.

The basic accuracy improvement over the learned present/marginal predictor is **0.8542**, with 95% group-bootstrap interval **[0.7708, 0.9375]**. The marginal predictor's 14.6% reflects its development-fitted interval prior and this sample's interval frequencies; it is not a theoretical chance level. No present-only predictor can select both differing futures correctly from the identical paired present. The recency baseline reaches 50% basic accuracy, showing why full ordered context matters here.

The transition baseline selected order 2 from orders 1–3 on development. Retrieval and relational context sizes/cutoffs were also development-selected; probability temperature, bin width and smoothing were fitted only on four calibration groups. Transformation-aware retrieval aligns complete observed context sequences, estimates their register shift and translates the remembered continuation. It was a capable competing mechanism, not a nearest-probe straw man. The relational readout uses explicitly supplied interval geometry, not a newly learned foundation representation.

[All group scores](results/heldout/groups.csv) · [All trial scores](results/heldout/trials.csv) · [Paired comparisons against every baseline](results/heldout/paired_comparisons.csv) · [Aggregate scores](results/heldout/summary.csv)

## Controls and uncertainty

For both successful mechanisms, in basic and transfer:

- **Reset and relevant-history removal:** accuracy returned to the marginal predictor's 14.6%, with zero paired success. The paired forecast distributions became identical. Reset was deliberate and logged; there was no capacity eviction.
- **History swap:** forecasts redirected exactly to the counterpart's expected continuation and retained 100% paired success. Scoring used the swapped answer.
- **Demonstration-order shuffle:** 100% accuracy remained. This control reversed complete demonstration chunks while preserving their internal transitions, so relevant evidence survived. It does not test arbitrary note-order destruction.
- **Ambiguous histories:** both alternatives received approximately **0.49952** probability, total **0.99904**, with maximum error from .5 of **0.00048**. Point accuracy was 50%, as expected for balanced identical-prefix futures. Mean log loss was **0.694108 nats**. Confident arbitrary choice was not counted as successful anticipation.

[Control checks](results/heldout/controls.json) and [ambiguity calibration](results/heldout/ambiguity_calibration.csv) include every mechanism. Brier is squared error against the known outcome distribution; on ambiguous cases, conventional expected realized Brier adds the irreducible constant .5. Intact outcomes are one-hot, so their Brier is conventional.

## Causality, budgets and validity

The separate predictor process imported only the acoustic model and numerical/standard libraries. Strict message schemas allowed fixed parameters, arrived waveform bytes, reset and forecast requests. An instrumented access guard blocked filesystem opens/listing, networking and subprocess access after startup, including a deliberate forbidden-open check. This is process/API isolation with instrumentation, not an adversarial operating-system sandbox.

Each forecast was appended to a hash-chained log and flushed with `fsync` before a reveal record and before the continuation reached the extractor. Logs preserve sequence numbers, timestamps, prefix hashes, memory hashes, distributions, point forecasts and code/config hashes. **All 48 held-out same-prefix future-substitution checks produced byte-identical forecasts.** Independent standard-library reconstruction matched all **3,456 held-out model distributions** within **2.23e-16**, and reconciled chronology, proper scores, budget parity, exact paired inventories, novel targets and zero eviction.

The full experiment used 36 groups: 8 development, 4 calibration and 24 evaluation. It ran 864 episodes plus 72 conservatively counted substitution probes, below the 1,000-stream cap. Blocks were .12 seconds, histories 14 blocks plus the probe, memory capacity 32. All numerical work ran locally with existing Python/NumPy. No paid compute, training of a foundation model, MERT download or additional experiment occurred.

[Held-out validity](validation/heldout.json) · [Append-only forecast/reveal/score log](data/heldout/events.jsonl) · [Arrived acoustic cache](data/heldout/arrived_cache.jsonl) · [Evaluator-only truth](data/heldout/truth.jsonl) · [Stimulus recipes/hashes](data/heldout/recipes.json)

## Provenance and reproduction

Held-out execution used committed revision **`4c9a87756f15fc1f458a3ffae9cd640661a637b3`**. The only untracked file at its start was the already-published preregistration receipt; all executable inputs matched the frozen commit. [freeze.json](freeze.json) identifies exact protocol, code, model and split hashes. The later publication SHA identifies the complete result snapshot and is reported in the PR receipt.

Development/calibration ran from the recorded base revision with isolated uncommitted source; their exact source snapshots, configuration and hashes are archived under each data split. Their preliminary forecasts used pre-calibration probabilities and are not confirmatory results. No held-out information was used for fitting. [Runtime/provenance summary](provenance.json) separates these stages.

For saved-output verification from this directory:

```sh
python verify.py heldout
python analyze.py heldout
shasum -a 256 -c CHECKSUMS.sha256
```

The verifier uses the standard library; the analysis uses NumPy. These commands reconcile saved forecasts and recompute summaries without extracting audio or rerunning evaluation. Output reproduction was checked byte for byte. The generator, split seeds, source snapshots, recipes and stimulus hashes are included for independently authorized replication. `run.py` refuses to overwrite a split's STARTED marker; no second tuned evaluation was run.

## Resulting action and limits

[selected_reference.json](selected_reference.json) retains `retrieval_transposed` with the frozen parameters as the reference for this demonstrated prediction capability. The relational readout is not selected as an advance. No subsequent experiment or standalone audit is authorized by this result.

The task uses clean synthetic monophonic blocks, externally supplied block boundaries, short fixed-capacity histories and an explicit continuation rule. It shows that ordered auditory history can change a committed forecast of unheard sound, including at a novel register, while ambiguity remains represented. It does not establish natural-music prediction, polyphony, long-term memory, perceptual identity or music appreciation. Ceiling performance here leaves broader differences between the mechanisms unresolved.

The estimator-provenance audit remains deferred. The worker publishes this one snapshot, records branch B, and stops awaiting review.
