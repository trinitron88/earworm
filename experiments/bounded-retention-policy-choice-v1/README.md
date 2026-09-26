# Bounded retention policy choice

Read `REPORT.md` in the completed publication for the decision and limitations. `PROTOCOL.md` and `configuration.json` define the preregistered comparison. `assignment.md` preserves the PM instruction.

- `materials.py`, `split.json`, `material-provenance.json`, `input-manifest.json` and `inputs/` preserve original inputs and rights/source provenance.
- `worker.py` handles arrived evidence and memory; `global_matcher.py` is an unchanged copy of PR20.
- `run.py` brokers label-free completed units to isolated workers and refuses to replay started readouts.
- `qualify.py` defines the15tiny predeclared fixtures; their first execution is saved under `qualification/`.
- `score.py` and `validate_outputs.py` independently read original saved predictions; they never import or execute the matcher.
- `outputs/` contains every started/finished response, compressed arrival ledger, stderr and integrity receipt.
- `freeze.json` identifies the actual execution snapshot before evaluation; `preregistration_receipt.json` links the earlier PR2 commitment. `publication.json` distinguishes execution and later publication.

For saved-evidence verification, use the existing local Python/NumPy environment to run `python validate_outputs.py development`, `python validate_outputs.py calibration`, `python validate_outputs.py evaluation` and `python score.py evaluation` from this package. Run these in a separate disposable checkout if preserving saved verification-file bytes. These commands do not regenerate inputs or execute any listener. Rerunning the scientific experiment is not part of this assignment.

This is clean symbolic observation with supplied segmentation, historical-work/fresh-excerpt material, a fixed partial query and one deterministic reservoir seed. It is not audio recognition or human identity measurement.
