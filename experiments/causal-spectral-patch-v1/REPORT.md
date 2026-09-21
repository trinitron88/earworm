# Spectral-patch execution validated; frozen reporting stopped on a condition lookup

**Status: INVALID reporting checkpoint. No complete scientific A/B/C decision.** Development, calibration and the one heldout audio run completed. Independent saved validation passes. The frozen analyzer then raised `KeyError: sp-16/joint/ambiguous/0`: its control lookup retained the prior study's `joint` condition name, while this study declares `unchanged`. The worker introduced this stale label while adapting reporting. It is a reporting implementation error, not evidence of an acoustic/runtime failure.

The frozen assignment stop rule prohibits a post-run repair/retry. The analyzer is preserved byte-identically, no analysis retry or audio rerun occurred, and no acceptance/rejection branch is inferred from the partial tables. All source, recorded audio, forecasts and partially written results are retained. `results/heldout/decision.json` is an explicitly authored invalid-failure receipt, not output from a completed gate computation. See [failure traceback](analysis_failure.txt) and analyze.py line63.

## Frozen design and selection

The front matches continuous log-frequency spectral patches, using64ms completed Hann windows or a multi-scale64/128ms pair on a16ms clock. The deterministic135-band,24-bins/octave projection covers80–3948.06Hz. Identity normalizes global energy and permits a bounded frequency shift plus monotone time mapping. Realization retains unshifted band power,absolute energy,PCM hashes/sample bounds and actual clocks; transformation and residuals are separate outputs. Matching does not use the frozen NSDF pitch readout, which only supplies a numerical continuation forecast coordinate.

The fixed search uses a16-frame query,earlier12/16/20-frame spans,integer shifts−6..+6 semitones and at mosttwo nonoverlapping matches. All thresholds and controls were frozen before audio. Comparators include the frozen prior f32 absolute/reference/single paths,trim16,MAP/mixture,whole-span/fixed-window,present,recency,transitions and a supplied-boundary oracle. Their code was not retuned.

Development compared both candidates on the same arrived stream, counting both channel/readout computations: single-scale source53/64,Brier0.3160744; multi-scale source55/64,Brier0.2283466. The frozen selection rule chose multi-scale. Calibration fit only the declared scalar temperature grid[0.015,0.025,0.05]. All log losses were infinite for unknown-only outputs; the declared Brier tie-break selected0.015. No representation,alignment,threshold or probability-floor repair followed.

40 fresh declared normalized motif identities were split8/8/24,excluding309 earlier identities and prior seeds. Prior saved full-waveform and non-silent unit hashes were checked; intentional within-study pairs/repetitions and captured-zero silence are explicit exceptions. A normalized family here includes the target/distractor contour and continuation magnitude; uniqueness is not a claim that every short musical substring is novel.

Transformations are separate: unchanged return; balanced nonzero transposition offsets−5,−3,+3,+5; uniform stretch0.8/1.25; or timbre change. No combined transformation or natural recording is included.

## Partial descriptive heldout tables—not a completed acceptance evaluation

Each cell contains48 intact outcomes from24 groups. These saved counts and scores are independently reproduced. They do not replace the missing complete controls/noninferiority/safety/gate report.

| Condition | Patch correct prior source | Patch correct forecast | Patch paired success | Frozen f32 absolute forecast | Frozen trim16 transition3 forecast | Supplied-boundary oracle |
|---|---:|---:|---:|---:|---:|---:|
| Unchanged |41/48|48/48|24/24|38/48|42/48|48/48|
| Transposition only |40/48|48/48|24/24|0/48|4/48|48/48|
| Stretch only |38/48|40/48|19/24|18/48|34/48|48/48|
| Timbre only |26/48|32/48|16/24|38/48|42/48|48/48|

Separate transformation labels: pitch-offset accuracy48/48 in transposition; timing-ratio accuracy27/48 in stretch; timbre-change classification18/48 in timbre. These labels are scored separately from source correctness. High forecast accuracy can coexist with an incorrect occurrence location. The timbre classifier is a preregistered residual threshold, not a validated human timbre percept. All three transformation labels, including unchanged-condition behavior, remain in recognition tables.

Forecast Brier by table order:0.0041774,0.0028300,0.2664471,0.6724916. Timbre log loss is infinite; zero probability on known outcomes is retained without clipping. Per-cell log loss,entropy,unknown mass,reliability bins,all57 model/front combinations and every control episode's raw scores are saved. The analyzer stopped before writing complete control summaries, comparator contrasts,family safety and the scientific branch. None is silently supplied by a replacement analysis.

## Integrity, causal isolation and preserved realization

Complete saved checks pass across25,560 heldout chained records,24,000 frozen comparator forecasts and3,360 patch forecasts. They independently reconstruct72,096 spectral channel-frames (identity error<=2.23e-16),the full patch search and probabilities (<=4.45e-16). Separate standard-library score arithmetic reproduces all27,360 scores within4.45e-16. Supplemental saved checks confirm1,108 reported match residuals and9,852 capture-status references; energy-residual error<=2.23e-16. All874 historical files are preserved.

Each query hash is durable before retrieval. Each forecast is fsynced before target PCM generation/extraction.96 heldout future-invariance probes and24 exact save/restores pass. The24 silence/missing transactions share existing probes: captured zeros remain observed silence; a missing span has a null PCM reference,generates no feature,advances the clock,flushes transient state and makes forecasts unavailable until reset. Restoring the saved probe recovers the original forecast bytes. This validates explicit discontinuity handling; it is not a claim of uninterrupted memory across lost samples.

Max audio-availability delay48ms; max chunk-dispatch to patch computation9.343ms; max first forecast-dispatch to durable commit75.54ms. These are separate clocks and are not backdated. They lie within the declared160ms bounds; the full scientific decision still remains incomplete.

Maximums:23 chunks,94,208 raw buffer bytes,85 retained patches (170 channel-frames),2,532,873 serialized output bytes,1,755 tested alignments/readout and1,917,872 reported search-array bytes. Filter matrix2,212,920 bytes; serialized config1,129,962 bytes; maximum full saved predictor-state snapshot5,641,772 bytes at the24 restore probes. Conservative temporary-array upper7,671,488 bytes and scalar-record upper10,240,000 bytes are reported separately. Full snapshots include comparator state,configuration,patches,caches,raw buffers and counters; these are serialized sizes/explicit upper bounds,not heap/RSS measurements or maxima at every instant. Archives are evaluator-only. Zero eviction means no long-term retention was tested.

## Resource and execution provenance

Exactly960 counted scientific streams:800 episode/control streams plus160 future probes.40 save/restores and40 transactional silence/missing checks share those probes. Both development candidate readouts are counted; no duplicate PCM pass or new smoke stream. Acoustic split runtimes52.35,52.77,161.45 seconds; conservative active elapsed accounting also includes design,validation and publication preparation. New artifacts are about914MB,under2GiB; time remains under7200 seconds; zero paid compute.

- Development freeze/execution: `5cc14365a2bb73212eb6ef221eac50b523128db3`.
- Calibration execution: `1214631a222ea84d0d97f9093eefb4ab108cff86`.
- Heldout execution: `d7586c0ca6667806bd99c859f83a1feee722649c`.
- Preregistration: PR2 comment5755482725,posted before heldout. Its descriptive calibration record count was corrected before heldout; criteria/source hashes did not change.
- Publication revision is distinct; the completion receipt records its exact SHA.

No scientific source changed after development. `validation/realization_checks.py` is a supplemental publication-time saved check of already-declared preservation requirements,not listener execution code. The model,reporter and frozen decision rules remain unchanged despite the report failure.

## Saved-only verification and files

From this package with the existing Python3.12/NumPy2.5 environment, `python -B verify.py development`, `python -B verify.py calibration` and `python -B verify.py heldout` reproduce the saved integrity checks. `python -B validation/independent_scores.py heldout`, `python -B validation/accounting.py heldout` and `python -B validation/realization_checks.py heldout` reproduce the saved arithmetic/accounting receipts. Do not rerun run.py,select.py or calibrate.py. The frozen `analyze.py heldout` currently raises the documented error; this snapshot does not claim a completed report pipeline.

Archives are lossless sequential gzip shards. Keep every `.jsonl.gz.partNNN.gz` alongside its base `.jsonl.gz`; `records.read_lines` reads all parts in order. Opening only the base gzip misses later records.

- [Frozen protocol](protocol.json), [filterbank](filterbank.json), [freeze hashes](freeze.json), [preregistration](PREREGISTRATION.md).
- [Selection](development_selection.json), [calibration scalar](calibration_fit.json), immutable `data/development/`, `data/calibration/`, `data/heldout/`.
- [Partial forecast summaries](results/heldout/summary.csv), [recognition summaries](results/heldout/recognition_summary.csv), [group scores](results/heldout/groups.csv), [reliability](results/heldout/calibration_bins.csv).
- [Full heldout validation](validation/heldout.json), [baseline validation](validation/baseline_heldout.json), [independent scores](validation/independent_scores_heldout.json), [realization checks](validation/realization_heldout.json), [state and clocks](validation/accounting_heldout.json).
- [Invalid receipt](results/heldout/decision.json), [missing report outputs](report_completion.json), [resources](resources.json), [provenance](provenance.json), CHECKSUMS.sha256.

## Stop and limits

Publish the complete invalid-reporting checkpoint and await review. A saved-only reporting correction would require a new bounded PM assignment; it has not been performed or self-authorized. No fourth front,architectural change,retuning or acoustic replay follows from this report.

The evidence is controlled synthetic monophonic material,short history andzero eviction. It establishes neither human perceptual identity,natural performance,polyphony,Bach familiarity,long-term transformed recognition nor appreciation. Human judgments remain a separate pilot.
