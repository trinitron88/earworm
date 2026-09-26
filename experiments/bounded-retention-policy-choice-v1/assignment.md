EARWORM_MERGED_SHA=b5acc1939c09fb1084bb9ccf72fbddbe061f3482
EARWORM_NEXT_INSTRUCTION_SHA=b5acc1939c09fb1084bb9ccf72fbddbe061f3482
EARWORM_ASSIGNMENT_ID=earworm-bounded-retention-policy-choice-v1
EARWORM_INSTRUCTION_VERSION=1
EARWORM_BASE_SHA=f93977b000e59ee9b7d8bcc6092510b156bd77de

## PR #20 reviewed disposition

Source: https://github.com/trinitron88/earworm/pull/20  
Reviewed publication: `b5acc1939c09fb1084bb9ccf72fbddbe061f3482`  
Execution revision: `30e1ffaa6285dc0ba09c53aca13490aefec95b39`  
Exact-head review: https://github.com/trinitron88/earworm/pull/20#pullrequestreview-5324880997  
Confirmed merge / successor base: `f93977b000e59ee9b7d8bcc6092510b156bd77de`  
Worker receipt: https://github.com/trinitron88/earworm/pull/2#issuecomment-5843807245  
Preregistration: https://github.com/trinitron88/earworm/pull/2#issuecomment-5843729275

Selected scientific branch: **Result B**, accepted and merged as a sound development snapshot. Independent review confirmed all288 saved readouts, exact agreement with the raw recount, byte identity of all105 reused session blobs and the frozen D/G/engine files, preserved construction provenance and resource compliance. Neither equal-observation method qualifies. D recovers24/24 source identities but fails timing and source-removal refusal; G achieves19/24 joint positive successes and improves source-removal refusal to3/24 but misses its stretched-cell and removal gates. The richer G-exact diagnostic achieves24/24 joint positives and rejects all fixed negatives, using additional exact onset/timing evidence. The paired-world certificate supports only compatible-occurrence-set/abstention semantics for deliberately identical origins; it is not a musical-panel impossibility certificate.

No CI statuses or PR-triggered workflow runs were reported; this is recorded as no CI, not passing CI. The merge-generated closed event is a no-op and does not reopen the completed assignment.

## Decision before assignment

**Which finish-line capability does this assignment establish or unblock?** Long-term transformed recurrence under an actual fixed persistent-memory capacity: retaining a once-heard occurrence through substantial similar interference and recent-buffer eviction, while distinguishing transformation recognition from the policy that decided which evidence survived.

**Decision: select or reject one simple bounded retention policy for the clean-observation memory ceiling before attaching a borrowed audio route.**

- **Result A →** at least one bounded policy meets every frozen evaluation gate while the unpressured ceiling is valid. Select the simplest passing policy in this fixed order: FIFO, fixed-seed uniform reservoir, then streaming diversity retention. Freeze it as the clean-observation retention reference for a later separately authorized audio/observation comparison. This is a memory-policy choice, not audio-route adoption or a release claim.
- **Result B →** the unpressured ceiling passes but no bounded policy passes. Reject all three tested bounded policies, preserve which required memories were lost and which refusals failed, and return the next PM decision to retention design versus observation-route work. Do not repair, enlarge capacity or substitute a policy in this assignment.
- **Result C →** the unpressured clean ceiling fails any identity/transformation/refusal gate. Withhold a retention conclusion because correspondence or task construction is inadequate even without capacity pressure; preserve the failure and return the next PM decision to the query/correspondence contract.
- **INVALID/resource-blocked →** preserve exact completed work, failure, owner and resume condition. No scientific branch is inferred.

**Stop condition:** one development/calibration/frozen-evaluation comparison of the three declared bounded policies plus the unpressured ceiling and present-only control; one complete publication, awaiting review, then stop. No automatic policy repair, acoustic run, MERT run, confirmation, polyphony or further capacity sweep.

This is a deliberate in-plan PM disposition after PR #20, not an automatic follow-up from its report. It uses the successful richer-observation route only as a labeled clean ceiling to isolate retention. The borrowed-audio direction remains open; perfect transformation estimation is not declared a permanent prerequisite.

## Frozen scope and material

Create `experiments/bounded-retention-policy-choice-v1/` from exact base above. Preserve PR #20, PR #19, PR #18 Result C, E08 and all historical code/models/results byte-for-byte. Root `PROJECT_STATE.md` changes only in the complete scientific publication.

Use **24 fresh phrase families**, split and hashed before any evaluation:
- 4 development families;
- 4 calibration families;
- 16 evaluation families.

Within each split, balance isolated monophonic Bach figures and newly generated unfamiliar motifs. Bach excerpts must be nonoverlapping with every prior saved phrase and separated from evaluation by work/excerpt family. Prefer already acquired, provenance-pinned public-domain symbolic material. The public-domain acquisition Brian previously authorized may be used only if the repository lacks enough nonoverlapping isolated material: one bounded source batch, exact URLs/license/source files/hashes saved before selection, no browsing for favorable outcomes. If the finite material cannot be constructed without overlap or selection shopping, checkpoint INVALID rather than replacing exposed families.

Each family has a once-arrived 12-event source, at least20 intervening phrase occurrences drawn from other frozen families/foils, then a query after at least64 seconds and actual eviction from a four-second recent buffer. The source must arrive before all interference. Candidate retention sees only arrived observations and its current state; it never sees query identity, future transformation, evaluator labels or archive data.

Keep transformations separate:
1. unchanged return;
2. integer transposition drawn from frozen nonzero shifts in -5…+5;
3. uniform time stretch drawn from frozen 0.8/1.25 scales;
4. convincing unrelated foil;
5–7. the three positive cells repeated after evaluator removal of every source-dependent persistent record/index/cache.

Do not combine transformations, add inversion or use another voice in this stage. Those remain later milestones.

## Observation ceiling and correspondence contract

Use PR #20's frozen G-exact global pitch/time correspondence and exact arrived note events as a separately labeled **clean observation ceiling**. This is evaluator-supplied phrase/event evidence, not audio, supplied boundaries, a qualified listener front end or an information upper bound. Keep the PR #20 G-exact implementation and transform ranges byte-identical unless an implementation failure makes the stage INVALID; no candidate repair here.

The query answer is:
- one compatible retained occurrence when uniquely supported;
- the complete compatible occurrence set when multiple retained whole occurrences are observationally equivalent;
- abstention when the stipulated origin cannot be identified.

Score set containment, set size and abstention separately. Never count an arbitrary member of an equivalent set as a uniquely correct origin. Musical-panel near matches remain ordinary alternatives unless their complete permitted observations are identical under the frozen contract. Preserve pitch shift, time scale, localization and refusal as separate outcomes.

Keep a no-persistent-memory/present-only control and an **unpressured ceiling** that retains all arrived occurrence records within a separately counted declared storage budget. The ceiling is not selectable. Its purpose is to distinguish capacity-policy loss from correspondence/task failure.

## Three fixed bounded policies

All bounded policies receive the identical sequence of immutable occurrence records and the same hard capacity: **8 complete occurrence records and at most256 KiB total predictor-accessible persistent state**, including descriptors, indexes, metadata, RNG state and caches. Scratch/RSS are counted separately. Every overflow must cause a recorded replacement; at least12 replacements per pressured session are required. No compression may hide extra occurrences outside the counted state.

1. **FIFO:** evict the oldest retained occurrence.
2. **Uniform reservoir:** standard fixed-seed streaming reservoir sampling over occurrences; record every RNG draw and replacement. No relevance score.
3. **Streaming diversity retention:** use one frozen transposition-normalized descriptor containing signed pitch intervals and globally normalized onset/offset timing ratios. On overflow, evaluate the nine-record set and evict the record whose removal maximizes the minimum pairwise descriptor distance among the eight survivors; tie-break by oldest arrival, then stable hash. No query-conditioned score, labels, future access, learning or post-calibration feature change.

Before calibration, specify exact descriptor arithmetic, normalization, distance, missing/constant handling and deterministic tie rules. Development may find implementation defects. Calibration may choose only one predeclared numeric descriptor weighting and the fixed G-exact abstention setting from a finite grid declared before calibration. Freeze them before evaluation. Do not change capacity, policy family, descriptor components or method after calibration exposure.

The source-removal intervention deletes every source-derived record and rebuilds all indexes/state from the surviving retained records. A match centered in removed source support is an integrity failure. The evaluation archive is never predictor-accessible.

## Gates and branching

Run all evaluation families once after a PR #2 preregistration receipt identifies the exact execution revision and hashes protocol/code/configuration, material split/provenance, all policies, descriptor/grid choice, input manifests, criteria and resource reserve. Development/calibration outcomes remain visible and are never reported as held-out evidence. Evaluation is phrase-family separated and frozen; no replay, exposed-family replacement or retuning.

For each selectable bounded policy, require on the 16 evaluation families:

- at least14/16 correct compatible-occurrence answers in **each** unchanged, transposed and stretched cell;
- at least14/16 joint compatible occurrence plus exact pitch shift in each positive cell;
- at least14/16 joint compatible occurrence plus time scale within10% in each positive cell;
- no more than1/16 accepted unrelated foils;
- no more than2/48 accepted substitutes across the three source-removal cells;
- source absent from the recent buffer in every scored case; capacity8 respected and at least12 persistent replacements recorded;
- no future/label/archive access, no hidden occurrence storage, and all evidence/resource/preservation gates pass.

The unpressured ceiling must meet the same scientific gates, except bounded-capacity/replacement gates, for Result A or B. If it does not, select Result C. The present-only control is expected to fail recurrence and is reported, not a selectable policy. Report both material strata, every family, compatible-set size, preservation, identity, shift, scale, refusal, replacement history, storage, compute and availability separately. No combined score may conceal forgetting or false acceptance.

When multiple bounded policies pass, choose the simplest in the fixed order above; do not manufacture superiority for the more complex policy. A bounded policy passing this clean ceiling does not establish acoustic recognition, continuous segmentation, human musical identity or complete long-term listening.

## Resources, publication and ownership

Hard cap: **900 total streams/readouts/probes**, **7,200 aggregate local compute seconds**, **2 GiB new artifacts**, **$0**. Count all policies, ceiling, present-only controls, development/calibration/evaluation probes, preparation, validation and publication. Reserve the complete frozen evaluation before first evaluation exposure. No paid compute, foundation-model training, new model download/change, audio rendering/extraction, MERT operation, controller training, deployment or force-push. No new acoustic-front work. If an actual usage limit intervenes, preserve progress and known reset/retry information, rest, and resume only unexecuted authorized work; no busy retry or replay.

Existing Actuator owns implementation/checkpointing; PM owns the next reviewed disposition. Reconcile this comment ID/version/base, receipt5843807245 and local processed-state tracking, acquire the existing no-overlap lock, and reuse any matching preparation. Live inspection found main at the merge SHA above and no open successor. Do not create another worker/reviewer or alter the existing30-minute continuation or persistent event task.

Publish one complete successor targeting main: draft → `earworm-review-ready` → ready, or update a matching active successor with the label present. Include scripts, exact inputs/hashes, preregistration, all raw outputs including failures, replacement/access ledgers, independently checkable scoring, resource/preservation ledger, actual execution revision and an ordinary PROJECT_STATE update preserving the finite checklist/first-release plan. Link the exact successor head and selected branch on PR #2, then stop awaiting exact-head review. No signal-only commit or work pushed only to merged PR #20.