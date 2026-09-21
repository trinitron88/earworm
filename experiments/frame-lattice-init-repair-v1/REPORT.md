# Initialization repaired; calibration validation stopped the study

**Invalid calibration integrity; heldout never started.** Pre-initializing the exact NumPy median helper before the unchanged audit guard resolved the earlier lazy-import failure. The one guarded smoke test passed init,20 arrivals,forecast,save/restore,reset and a deliberately forbidden open. Forecast bytes were identical after restore, and only the two deliberate open probes were blocked. The model, scientific rules, comparator code, selection objective, metrics and gates remain byte-identical to PR #14.

The repaired worker then completed development and calibration without another guard failure. Calibration's frozen validator stopped on four spectral-shape normalization assertions. The assignment explicitly requires stopping before heldout when calibration integrity fails, with no second repair. No guard relaxation, retuning, rerun, replacement group or heldout audio generation followed.

## Concrete calibration edge case

All four affected cached frames contain exactly one nonzero PCM sample, at index0. Their eight spectral-shape values are all0, while unwindowed RMS is nonzero (.005935,.000412,.004618,.003772). The frozen model computes spectral shape after multiplying by a Hann window; its endpoint weight is0. Thus the saved zero spectrum and nonzero unwindowed energy are consistent with different measurement supports. The frozen check nevertheless requires spectral-shape sum1 whenever unwindowed RMS>=1e-8.

This identifies a validation assumption at an endpoint-only frame, not a demonstrated corruption of the captured audio. We did not alter that assumption or claim the full calibration validator passed. The PCM hashes, sample indices/values and cached features are recorded in [calibration_integrity_failure.json](calibration_integrity_failure.json). The diagnostic only inspected saved bytes and scalars; it ran no FFT, NSDF, listener or new audio pipeline.

Affected records: `fir-15/detached/intact/{0,1}` frame49, samples6272–6784; `fir-15/legato/intact/{0,1}` frame50, samples6400–6912. Four failures among25,888 retained calibration lattice-frame records. The last availability sample is7168. Nothing was removed or substituted.

## Scope and prepared scientific comparison

The runtime edit is only two fixed `np.median` initialization calls before the audit hook. Worker guard and request loop are byte-identical. The smoke buffer is fixed and independent of all scientific seeds. [Preflight](preflight_result.json), [source hashes](scientific_source_hashes.json).

Forty fresh normalized groups exclude269 prior identities, including all failed-stage groups; all waveform seeds are new. The original f32/f48/f64 grid,8 ms hops,24-frame query,19/24/29-frame monotone alignment, bounded matching and fixed probability rules are unchanged. Frozen event fronts remain comparators, never inputs to the lattice path. No parameter is fitted during calibration.

Development validation passed8,192 chained records,10,560 reconstructed forecasts,32 future-invariance probes,8 save/restore checks and685 historical hashes. Its fixed rule selectedf32: source accuracy.8125, Brier.375132, matched-query coverage.742839. The f48/f64 policies failed the declared development coverage feasibility criterion. These are development-selection results, not final acceptance.

For transparency, the unmodified scientific analysis was run on the saved calibration outputs with an explicit **failed-validity receipt**. It retains branch`invalid` and all outcomes. Exploratory reference forecast scores are9/16 detached,9/16 legato,7/16 duration and7/16 joint; trim16, MAP and oracle reference are16/16 throughout. Calibration source accuracy is.4375, unrelated false-match rate0, and joint selected-minus-strongest-comparator-.5625. These small calibration summaries are not held-out evidence or a basis for retuning, adopting or rejecting the representation. The complete model/cell/control, recognition/transformation, uncertainty/calibration, alignment and safety tables remain in [results/calibration](results/calibration/).

## Evidence and validation limits

Both scientific splits completed160 episodes,32 future-invariance probes and8 save/restore checks each. The latter share existing probes and add no scientific streams. All captured PCM, frame candidates/unknown mass, spectral/energy measurements, bounds/hashes and actual clocks, alignments, pre-reveal logs and original/comparator observations remain available. No partial archive was reconstructed.

The full calibration validator exited at its spectral normalization assertion. `validation/calibration.json` is a failure receipt authored from that observed exit, not a fabricated successful verifier result. Independent saved-only checks separately verify both complete log chains (8,192 and8,216 records), the sixteen unchanged scientific files, unchanged guard/worker loop,685 historical hashes, preflight hashes and absence of heldout. Independent standard-library scoring reproduces all8,000 calibration forecasts within4.44e-16. Those narrower checks do not override the failed integrity gate.

[Development validation](validation/development.json), [preserved-attempt checks](validation/preserved_attempt.json), [calibration failure receipt](validation/calibration.json), [independent calibration scores](validation/independent_scores_calibration.json), [decision](results/calibration/decision.json), [provenance](provenance.json), [checksums](CHECKSUMS.sha256).

Saved-only reproduction:

```sh
python experiments/frame-lattice-init-repair-v1/validation/preserved_attempt.py
python experiments/frame-lattice-init-repair-v1/validation/independent_scores.py calibration
```

The unchanged `verify.py calibration` is expected to reproduce the failed assertion. Do not rerun `run.py` or `preflight.py`; their authorized attempts are complete. No heldout freeze/preregistration was posted because this stage stopped before that point.

## Cumulative budget and stop

384 scientific streams consumed (320 episodes+64 future probes), plus one prior failed stream and one fixed smoke stream:386 conservatively counted streams.576 heldout streams remain unused. Full planned accounting would be960 scientific+one historical failure+one smoke=962, below the1,000 hard cap. Save/restore is included within existing probes. Scientific extraction counters:109,184 lattice calls,48,406 frozen aggregation calls and3,683 trim16 calls. Scientific split runtime80.161 seconds; smoke runtime.244 seconds. The prior840.093-second conservative charge is retained, with current wall time charged conservatively against the6,300 additional-second limit; see [resource ledger](resources.json). Original failed detailed counters remain explicitly unavailable. Combined new artifacts remain below2 GiB; no paid compute or download.

Publish this complete invalid-calibration snapshot and await exact-head review. The initialization repair succeeded operationally, but the scientific study has no confirmatory result. A correction to the normalization check is an unexecuted proposal requiring the PM's next bounded decision; no second repair is made here. Earlier crop/aggregation negative results remain unchanged. No human perceptual identity, natural-music, nonzero-transposition, polyphony or long-term-memory capability is claimed.
