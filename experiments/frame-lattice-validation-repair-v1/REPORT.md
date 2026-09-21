# Support-consistent validation clears execution; the frozen lattice fails advancement

**Decision: branch C.** The one authorized saved-validation correction passes, so the reserved heldout stage was run once. The fixed f32 lattice/readout fails source recognition, transformation labeling, forecast advantage, proper scores, ambiguity, paired success and family safety. Reject this design for advancement and checkpoint the continuous-representation prerequisite. Do not resume crop/window/aggregation micro-repairs. A further action requires the PM's next bounded assignment after review.

## What changed and what stayed frozen

Only the measurement validator changed: it reconstructs unwindowed RMS and Hann-windowed eight-band power independently from saved PCM, comparing every value within1e-12. The correct normalization denominator is max(total band power,1e-20). Four calibration frames contain only one nonzero endpoint sample; their nonzero RMS and all-zero Hann spectrum are consistent. Full saved development/calibration validation passes with zero acoustic reconstruction error. Details and the old assertion are in [VALIDATION_CHANGE.md](VALIDATION_CHANGE.md) and the isolated verify.py diff.

PR15's model, worker/guard, broker, f32 selection, protocol, configuration, split/seeds, retrieval/alignment, comparator implementations, metrics, bootstrap and gates remain byte-identical. Development/calibration data and published calibration outcomes are reused exactly. The historical invalid calibration decision remains preserved, not relabeled as a new result. All763 historical files remain unchanged. No development/calibration replay, fitting, selection or second preflight occurred.

[Preregistration](PREREGISTRATION.md) was posted before heldout creation as PR2 comment5755058327. Heldout executed from **6303e0036069465d5b6cd67ab3d46975c0a70568**; the publication commit is distinct. The unchanged broker's legacy source-prefix check is supplemented by exact new-package commit binding; see freeze.json and validation/preexecution_commit_binding.json.

## Heldout evidence

24 reserved phrase groups;480 scored episodes/control streams plus96 future probes=576 counted streams. Save/restore shares24 of those probes. No group was replaced or repeated. Counts below use48 intact query outcomes/cell; paired success requires both members within each of24 groups.

| Intact condition | f32 correct source | f32 correct forecast | f32 paired success | Strongest joint comparator forecast | Supplied-boundary oracle forecast |
|---|---:|---:|---:|---:|---:|
| Detached |34/48|34/48|15/24|48/48|48/48|
| Legato |32/48|34/48|15/24|44/48|48/48|
| Duration change |27/48|30/48|13/24|44/48|48/48|
| Joint changes |22/48|25/48|10/24|46/48|48/48|

The strongest non-oracle comparator under the frozen joint-accuracy rule is trim16/transition3 (ties broken by model name). All50 model/front combinations, including MAP/mixture, absolute/single-window, present, recency and transitions, remain in the result tables. Strong comparator accuracy here does not reverse its earlier failed acceptance gates or authorize adopting it.

**Recognition and transformation.** Source accuracy115/192=59.9%, below90% overall and80% per-cell gates. Similar-unrelated false match is0. Transformation accuracy in the declared changed conditions is0: the frozen label requires correct source, correct pitch offset and correct time ratio together. It is not a pure pitch test. All true uniform pitch offsets arezero; this establishes nothing about nonzero transposition. Alignment coverage is reported separately (about85.2%,80.8%,81.9%,76.1% by the table's cell order); high valid-pitch coverage alone does not establish the correct source or duration mapping.

**Prediction and proper scores.** Joint f32 accuracy52.1% versus95.8% for the strongest comparator. Paired equal-group difference is−43.75 percentage points, bootstrap95% interval[−60.42,−27.08]. Its lower95 advantage over present-only is+18.75 points, which is insufficient: the preregistered requirement was positive advantage over both present-only and the strongest comparator. Oracle forecasts are correct in all intact cells. Joint Brier increase versus oracle is0.7730876523, above0.02; log-loss increase is infinite because some known outcomes receivezero mass (including unknown-only outputs), retained without clipping. All four familywise noninferiority gates fail. Reliability, entropy and unknown mass are separately tabulated.

**Causal controls and uncertainty.** Reset and relevant-memory removal pass their frozen dependency controls. Swap distributions are exactly equivariant (error0), but the required swap paired success is only10/24, so the composite causal-control gate fails. Shuffle passes (accuracy drop1/24); ambiguity fails. These failures do not negate passed arrived-only isolation and pre-reveal checks or demonstrate future leakage. Every rendering family's accuracy loss versus oracle exceeds0.10: pure0.4583, fundamental0.2083, overtone0.3854.

**Preservation, clocks and state.** Full heldout validation checks25,240 chained records,24,000 forecasts,79,808 retained lattice frames,96 future probes and24 restores. Energy/spectral reconstruction error iszero; forecast reconstruction error<=3.34e-16; separate24,000-score arithmetic error<=4.45e-16. Raw sample bounds/hashes, original measurements, source alignments and interpretations remain separately saved. Completed-frame audio availability delay max56ms; chunk-dispatch to frame computation max9.27ms; forecast-dispatch to durable commit max58.52ms. The frozen160ms gates pass with no backdating. These clocks have different origins and are not silently substituted for one another.

Maximums:23 arrived chunks;94,208 raw buffer bytes;181 lattice frames;361 comparator frames;23 events/front;2,090,488 serialized listener-output bytes;2,326 serialized configuration bytes;120 candidate alignments and55,705 serialized scratch bytes per readout. Raw buffers, retained measurements/forecasts, configuration and scratch are counted separately; evaluator archives are inaccessible to the predictor. Serialization is not a full Python heap/RSS measurement; pending references/counters and interpreter overhead are not inferred from it. There waszero eviction. See [saved accounting](validation/accounting_heldout.json).

## Interpretation and limits

The previous execution-invalidity was a validator support error, not corrupted audio. Correcting it exposes a substantive failure of this particular fixed-cadence lattice plus frozen query/alignment/readout design. It does not prove that all continuous representations fail, nor that useful musical information is absent from the measurements. This study does not isolate which design component is responsible; no extra diagnostic or repair was run.

This is controlled monophonic synthetic material, a short buffer and one forecast horizon. It does not establish perceptual identity, natural music, polyphony, nonzero transposition, persistence beyond eviction, human-like listening or appreciation. Human judgments remain a separate pilot.

## Reproduce checks from saved evidence

Use the existing Python3.12/NumPy2.5 environment. From this package, run `python -B verify.py development`, `python -B verify.py calibration`, `python -B verify.py heldout`, `python -B validation/preservation.py`, and `python -B validation/independent_scores.py heldout`. These read saved evidence; the validator reconstructs only the explicitly authorized RMS/spectrum and saved alignment/forecast arithmetic. `analyze.py heldout` reproduces the frozen tables and branch. Do not rerun run.py, preflight.py or select.py; STARTED receipts and immutable prior execution sources are included.

- [Decision and gates](results/heldout/decision.json); [all forecast summaries](results/heldout/summary.csv); [paired/group trials](results/heldout/groups.csv).
- [Recognition](results/heldout/recognition_summary.csv); [individual alignments](results/heldout/recognition_trials.csv); [familywise comparisons](results/heldout/comparisons.csv).
- [Controls](results/heldout/controls.json); [family safety](results/heldout/safety.json); [reliability bins](results/heldout/calibration_bins.csv).
- [Heldout validation](validation/heldout.json); [preservation](validation/preservation.json); [independent scoring](validation/independent_scores_heldout.json).
- [Resources](resources.json); [provenance](provenance.json); [frozen sources](freeze.json); CHECKSUMS.sha256.

Cumulative962 counted streams; zero paid compute. Combined failed-prefix/PR15/continuation storage is about643MB, below2GiB. The cumulative7200-second ceiling includes prior1547.20676s,335s conservatively charged for the interrupted setup, and resumed active-turn elapsed time; scheduler idle gaps are excluded. Exact report-time accounting is in resources.json.

Publish this complete successor, await exact-head review and stop. No second study or architecture change is authorized by this report.
