# Project Earworm — review state

## Current status

**Experiment 08: Competing accounts is complete.** This snapshot awaits review in [issue #1](https://github.com/trinitron88/earworm/issues/1). No subsequent experiment has started. Publishing this snapshot does not authorize or schedule a new run. Completed experiments were not rerun, evaluation rules were not changed, and source was not refactored for this handoff.

The long-term aim is auditory representation and memory that help AI interpret music. This run tests a much narrower engineering behavior: source retrieval and competing accounts of edits to synthetic monophonic phrases. It does not establish human musical identity or subjective hearing.

## Evidence and interpretation

- Sixteen held-out phrase groups, 576 source-present primary queries, and matched source-absent histories. Variants within a group are correlated.
- New reader: **164/576 accepted correct memories**, versus frozen Experiment 07 reader **198/576**. Both have **0/576 observed absent-source false acceptances**. This is not a retrieval improvement.
- **553/576** correct memories rank uniquely first when the true source is stored. Ranking ignores rejection and is a post-hoc diagnostic, not successful emitted retrieval.
- Accepted memory plus strict programmed edit recovery: **156/576**. Missing+transposition **8/32**, missing+timing **8/32**, missing+detuning **0/32**. Each combination ranks correctly and recovers its programmed edits with an oracle reference in 32/32 cases; oracle results are not retrieval.
- Eight accepted weak-note cases retain unresolved observation because energy remains despite a missed event detection. **All 64 masked cases are rejected**, so uncertainty-aware accepted retrieval under masking remains unmet.
- Ambiguous source pairs: exact sets for 4/16 unique cases (eight decisions across two orders), versus 12/16 for the old reader. For substitutions, the programmed correspondence appears in 31/32 alternative sets but 0/32 best paths with an oracle source. Substitution and deletion-plus-insertion can explain the same sound; construction history is not a uniquely audible cause.
- Previously completed verification: 84 fresh sequential replays / 840 blocks, four future-prefix pairs, reference-drop/reset controls, and output-availability timestamps. These archived checks were **not rerun for publication**.

Interpretation: usable relational information often remains, while support calibration across evidence quality and phrase length is weak. This is a diagnosis from the frozen results, not proof that lowering a threshold would be safe or that the encoder alone determines the failure.

## Exact paths

| Artifact | Repository path |
|---|---|
| Frozen rules, splits, scoring, source hashes | `work/accounts_results/protocol.json` |
| Frozen readout weights and thresholds | `work/accounts_results/frozen_config.json` |
| Reader and competing accounts | `work/accounts_reader.py` |
| Extraction, development, evaluation, replay runner | `work/accounts_experiment.py` |
| Deterministic renderer, seed 2026091908 | `work/accounts_stimuli.py` |
| Full generation truth, exclusions, expected PCM hashes | `work/accounts_stimuli/manifest.json` |
| Unchanged acoustic extraction | `work/remember_changes_acoustics.py` |
| Frozen old baseline and alignment | `work/confidence_reader.py`, `work/incomplete_matcher.py` |
| Old baseline configuration | `work/confidence_results/frozen_config.json` |
| Main results by method/family/group/length/control | `work/accounts_results/summary.json` |
| Individual primary saved decisions, all four readers | `review/experiment08/primary_trials.csv` |
| All delay/reset condition summaries | `review/experiment08/control_summary.csv` |
| Ranking and oracle diagnostics | `work/accounts_results/posthoc_diagnostics.json` |
| Ambiguity decisions | `work/accounts_results/ambiguity.json` |
| Fresh replay records and actual/simulated timestamps | `work/accounts_results/fresh_replays.json`, `work/accounts_results/swapped_replays.json` |
| Future-prefix checks and replay summary | `work/accounts_results/prefix_checks.json`, `work/accounts_results/replay_summary.json` |
| Scoring caveats | `work/accounts_results/metric_definition_note.json` |
| Original audit and portable-reproduction findings | `work/accounts_results/audit.json`, `work/accounts_results/portable_validation.json` |
| Report, figures, milestone | `outputs/competing-accounts-report.html`, `outputs/competing-accounts-results.png`, `outputs/competing-accounts-observations.png`, `outputs/experiment08-milestone.md` |
| Four report examples as saved structured evidence | `review/experiment08/report_examples.json` |
| Dependencies and Python version | `requirements.txt`, `.python-version` |
| Snapshot sanitization and file provenance | `REVIEW_SNAPSHOT_MANIFEST.json`, `SHA256SUMS` |

## Original source revision

**No original Git commit is available.** The experiment ran in a local directory that was not a Git checkout. Do not treat this later upload commit as the revision on which the run originally executed.

The original protocol was frozen at `2026-09-19T07:35:44.263852+00:00`; the fitted readout was frozen at `2026-09-19T07:36:18.789612+00:00`, before held-out feature extraction. The six SHA-256 values recorded in `protocol.json` identify the frozen generator, reader, runner, and three helper modules. Those files and both frozen JSON records are published byte-for-byte. The later audit/report/packaging helper sources are included unchanged as provenance, but were not part of that six-file pre-evaluation hash set.

The full manifest changes only machine-specific audio paths. Its exclusion patterns, random seed, notes, group assignments, and expected PCM hashes are unchanged. The portable-validation record redacts its local directory. Report delivery links/footer are adapted to this repository. Snapshot CSVs are selections/aggregations of existing saved decisions, not fresh evaluations. See `REVIEW_SNAPSHOT_MANIFEST.json` for hashes and individual treatments.

## Reproduction

These commands are provided for a later, explicitly chosen reproduction. **They were not executed as part of this publication.** Use a disposable checkout because the unchanged runner writes regenerated manifests/results into its original relative locations.

Python 3.12.14 was used; the direct numerical/report dependencies are pinned in `requirements.txt`. There is no model download or MERT invocation in Experiment 08.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B work/accounts_stimuli.py --saved work/accounts_stimuli/manifest.json --outdir work/accounts_stimuli
.venv/bin/python -B work/accounts_experiment.py develop
.venv/bin/python -B work/accounts_experiment.py evaluate
.venv/bin/python -B work/accounts_experiment.py replay
```

The saved-manifest option supplies all 1,032 excluded earlier interval patterns without requiring prior experiments. The renderer uses seed 2026091908 and regenerates 1,128 two-second WAVs, approximately 210 MB. It writes a new routing file containing only IDs and paths. Generation metadata remains outside predictor inputs. The runner extracts 328 development and 752 held-out blocks; 48 stacked development queries are unused. Development refits 1,200 labeled candidate pairs and reproduces the calibrated threshold. Evaluation runs the core families and then the three stacked families sequentially using the frozen configuration. The original frozen source-hash check remains active. Wall-clock times and machine throughput will differ.

Compare regenerated `summary.json`, readout coefficients/thresholds, and the saved primary rows; compare generated PCM hashes with `review/experiment08/waveform_hashes.csv`. The original run already included a separate relocated validation that regenerated all 1,128 identical waveforms, reproduced development fitting/calibration, and checked four held-out waveform pairs. The archived `portable_validation.json` documents that completed check; it is not a new validation of this upload.

The full 45 MB development/held-out alignment tables, full batch-trial JSON, detector caches, prior file inventories, and large audio collection are omitted. The runner regenerates the evaluation products. `accounts_audit.py` additionally verifies 12,351 files from earlier local experiments; those archives are not included, so its whole-project preservation check cannot run from this snapshot alone. `accounts_report.py` and `accounts_portable.py` are the unchanged historical helpers and expect the larger generated artifacts. Use the already-published report for review; no packaging-only refactor was made.

For a read-only integrity check of this snapshot (no model or experiment execution):

```sh
shasum -a 256 -c SHA256SUMS
```

## Known limitations and unresolved questions

- Four fitting groups and four calibration groups; limited evidence for generalization. Accepted damaged phrases beyond simple controls occur only in the six-event groups.
- Supplied completed two-second windows, an unchanged monophonic detector, engineered operations and quality filters, and a limited alignment beam remain assumptions.
- Explicit capacity 12 acoustic memory with no learned decay/interference mechanism. Causality is at completed-window availability, not frame-by-frame live audio. Simulated arrival times and measured wall times are recorded separately.
- A quiet predicted location supports an acoustic statement under an alignment; it does not identify the physical cause. Missed detections must not become fabricated observations.
- Ordinary origin scores use generator provenance, not human identity. Oracle recovery and ranking must stay separate from accepted retrieval. Empty joint columns for baseline readers mean not evaluated.
- MERT stays frozen and unused in this run. No polyphonic/natural music transfer or human identity judgments are established; the human pilot remains separate and is not included.
- Is the main rejection problem caused by support calibration, feature scaling/count dependence, sparse development coverage, or a combination? The results do not isolate these causes.
- What evidence would justify an accepted memory under masking while keeping the event's cause unresolved? Can competing accounts be retained without rewarding invented missing notes?

A bounded recommendation for the subsequent reviewer is to inspect calibration and feature treatment against the saved length/observation controls, identify evidence versus inference, and propose one focused next action in issue #1. This recommendation does **not** start or authorize another experiment.

## Publication boundary

The snapshot is limited to this experiment and its helper code. No credentials, personal/employer documents, model weights, caches, virtual environments, full prior workspace inventory, or large generated audio collection are included. Five short synthetic audio examples remain embedded in the report (10 seconds total). No project-wide working directory or local configuration is uploaded. Repository visibility remains private. There is no automatic worker/reviewer loop.
