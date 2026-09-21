# One support-consistent validation correction

The old assertion required normalized Hann spectral bands unless **unwindowed** RMS was tiny. This confused two different measurement supports.

The corrected validator independently reconstructs unwindowed RMS and Hann-windowed eight-band power from saved little-endian float32 PCM; each saved value must agree within the existing 1e-12 tolerance. Normalization is total power / max(total power, 1e-20). It does not import or call the acoustic model or worker. All other integrity/reconstruction checks remain in place. This is a saved measurement check, not a feature replacement or listening rerun.

Development: 76,416 frames; calibration: 25,888 frames. Both pass with exactly zero energy/spectral reconstruction error. Calibration retains the four endpoint-only frames (one nonzero sample at index zero): RMS is nonzero, Hann power zero, all eight bands zero. See validation/calibration.json for samples and hashes. Forecast reconstruction passes at <=3.34e-16; independent calibration score arithmetic at <=4.45e-16. All 763 historical artifacts are unchanged.

The entire original data directories, development selection and calibration result files are reused byte-for-byte. The historical invalid decision remains as a historical result in results/calibration/decision.json; the new integrity receipt does not silently rewrite that publication. No new development/calibration pipeline, reselection, fit, or preflight occurred. The only forthcoming acoustic execution is the already reserved heldout split, conditional on preregistration.

The runtime has a legacy source-check prefix pointing to the PR15 package. It remains byte-identical. freeze.json limits that legacy comparison to unchanged files, binds all new execution code separately, and records the distinction. Before starting, the new-package hashes will also be checked against the exact execution commit; the broker additionally checks the aggregate top-level source hash. This preserves both runtime identity and provenance.
