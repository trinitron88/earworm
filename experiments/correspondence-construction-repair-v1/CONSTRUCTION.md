# Independent complete construction relation

This evaluator-side repair changes only the two terminal historical-window
source/foil checks in the original generator. It does not import or call D, G,
the engine or any model. The original PR #19 package remains unchanged.

`materials_repaired.py` is the frozen original `materials.py` with only its
terminal source/foil checking block replaced by a callback. `construction.py`
verifies the original hash and exact permitted text replacement before loading
that copied module. The source extraction, seeds, nonreuse checks, foil rules,
interference rules, sampling, query support and all unrelated checks stay intact.

For two ordered twelve-event arrays, complete equivalence requires one integer
pitch translation and one positive affine time map. First onset and final offset
determine the unique proposed scale and offset. Every one of the twelve onsets
and twelve offsets must agree with that same map within **1e-9 seconds** absolute
arithmetic roundoff. This fixed tolerance is much smaller than musical timing or
the sampling interval; it is not fitted to data or a matcher. Checking both ends
of every event also checks every intervening rest. Guard transformations are
unrestricted positive scale/integer shift: they define complete construction
equivalence independently of the narrower candidate-search ranges.

All earlier contiguous twelve-event windows, including figure boundaries, are
scanned. Only the source window starting at event index 2 may fully match the
source. Neither foil may have any full equivalent earlier window. Pitch-only
matches remain explicit diagnostics and no longer independently veto a panel.
Every window's pitch differences, scale, offset, 24 endpoint residuals and full
equivalence decision are saved. Positive-query checks are also saved, while the
query veto applies only to the two foil cells.

The full source, query and history arrays are written before the checks run, and
all check results are saved before a construction rejection. Newly generated
evidence is labeled as this new preparation. It does not recover or replace the
missing original PR #19 failing arrays.

## One-use panel assembly

Root calls `construction.build_panel(outputdir)` once. A nonempty output
directory is refused. The procedure verifies and copies all 105 original session
files byte-for-byte, then reconciles the 35 saved sessions using their saved
exact-event histories and separate evaluator labels. Their original labels are
preserved unchanged; corrected construction evidence is kept in sidecar files.

Only `novel-20260926-04`, seed **202609260103**, is newly constructed. Its source
and eight fixed interference figures are generated once. The source is checked
against the same historical development-signature registry and the seven reused
family signatures. Its five fixed sessions are then built once each. Any failed
unchanged guard or corrected terminal guard stops the process. No seed, excerpt,
figure or query is replaced; no candidates see a partial panel.

Every terminal check writes `construction-witnesses/<session_id>.json`. The new
source and fixed figures are also saved in `new-family-construction.json`.
`preparation-provenance.json` records source revisions, hashes and new timestamps.
On failure, `construction-failure.json` preserves the checkpoint and witnesses;
Result B withholds the panel for PM disposition.

On successful construction, the sole consumer contract is
**`input-manifest.json` with `sessions[].session_id` and `sessions[].path`**.
The manifest contains 40 sessions, hashes of all three files per session, origin
tags distinguishing 35 byte-identical reused sessions from five new sessions,
and hashes of all 40 construction witnesses. There is no `manifest.json`/`id`
alias. Root separately validates packaging, scoring, access and resources and
preregisters the complete execution before any first musical comparison.
