# Borrowed recurrence feasibility v1

One authorized comparison of established temporal audio matching, frozen local MERT features and a separately isolated clean-score reference. The question is once-heard recurrence after 32 seconds of interference and eviction from the recent audio buffer, with transformation and retained realization evidence measured separately.

Start with:

- `results/evaluation/REPORT.md` — result, uncertainty, limitations and stopping decision.
- `results/evaluation/analysis.json` — every route, cell, material stratum, control, bootstrap interval and gate.
- `results/evaluation/validation.json` — independent saved-artifact checks, without prediction/model reruns.
- `results/evaluation/resources.json` and `publication.json` — measured and conservatively charged resource use.
- `PROTOCOL.md`, `freeze.json`, `preregistration_receipt.json` — exact rules and before-evaluation execution provenance.
- `sources/manifest.json` and `provenance/` — exact public-domain source files and archived rights evidence.
- `checksums.json` — publication file integrity (excludes itself and disposable Python bytecode).

Each session directory contains immutable `audio.npz`, `measurements.npz`, `ceiling.npz`, labels, arrival/availability logs, flushed response-before-label records, predictions and summary. The audio listener never receives score labels or source/query boundaries. MERT row coordinates are nominal pooled time bins; full one-second context and actual output availability remain separate. The score reference runs in its own child.

`results/development/` preserves all selection evidence, including the unselected MERT layer and negative outcomes. Its first session was a checkpoint within the same 32-session development run, not a repeated probe. `preparation/README.md`, the early material inventory and initial ledger are historical preparation records from before the material amendment. Their blocked status is superseded by the material manifest, development/evaluation evidence and publication checkpoint, not erased.

## Scope

The material is deterministically rendered isolated Bach score figures plus newly composed monophonic motifs. It is not natural-performance, polyphony, fugue comprehension, human unfamiliarity, perceptual identity or appreciation evidence. Query matching uses a fixed recent fragment and a deliberately simple borrowed alignment/readout. The MERT route is hybrid because chroma from the acoustic sidecar estimates pitch shift after feature-based matching.

The persistent cap was enforced, but these sessions did not create FIFO replacement pressure. Retention under delay/interference and survival under memory-capacity pressure are different claims.

## Reproduction and review boundaries

The existing local Python environment supplied NumPy, PyTorch, transformers and SciPy. No dependency, encoder, soundfont or renderer download was performed. Musical-source downloads alone were authorized, explicitly public-domain and 123,847 bytes. Local MERT weights are not uploaded; their hashes/config and compatible strict loader are recorded.

`runner.py` owns truth and immutable archives. `listener.py` receives arrived PCM only and disables file/network access after initialization. `validate.py`, `analyze.py`, `summarize.py` and `make_report.py` operate on saved evidence. `materials.py` prevents accidental evaluation generation without explicit opt-in, and `runner.py` additionally requires the posted preregistration and unchanged frozen hashes. Reproduction is not authorization for a second experiment; existing completed sessions must not be rerun or criteria retuned under this assignment.

No historical experiment files, main branch, model weights, reviewer configuration or scheduled worker limits were changed. The successor is published for the existing exact-head reviewer, with no automatic repair or new experiment afterward.
