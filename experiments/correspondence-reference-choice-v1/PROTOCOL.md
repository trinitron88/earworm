# Development correspondence reference choice — preparation specification

Status: **construction-invalid before preregistration and musical exposure**. This document assembles the implemented preparation choices and the PM's authorized protocol for review. It is not a retrospectively claimed preregistration. The complete authoritative assignment is `assignment.md`, comment5842993369/version1, base07651558671fdaf57b5685284079cea021b0ea88.

## Intended decision and fixed candidates

D is the byte-identical PR18 `matching.py` plus `listener.py::predict(state,"ceiling")`: last-two-second query, integer shifts−5…+5, unweighted skip recurrence, single-path duration rejection, span-ratio estimate and zero acceptance threshold. Wrapper reporting does not alter this function.

G uses one global map `query_time = scale * history_time + offset`, `query_pitch = history_pitch + shift`, with scale[0.65,1.5], shift−5…+5. The S1-inspired exhaustive candidate enumeration and full-consistency verifier are specified in GLOBAL_METHOD.md. No fitted timing tolerance or musical-data threshold search is used. Identical sampled pitches/silence at100ms centers, occupancy, unit IDs and completed-unit availability go to D and G. Original rows remain unchanged.

G derives only maximal constant-pitch runs. Its transition times are open-left/closed-right brackets between adjacent centers. Clipped outer edges are coverage constraints, not hidden onsets; adjacent repeated pitches merge; missing observations and removed units divide support. It returns every admissible region, explicit correspondences and feasible parameter ranges. Multiple distinct consistent regions cause abstention; serialization order never chooses an identity. Parameters can remain uncertain even when the reported representative happens to score correctly.

G-exact is a separate diagnostic using exact monophonic event intervals on the same center-to-center support and retained history. Unit-arrival clipping is explicitly marked and only genuine continuation edges are rejoined. It cannot provide events, candidates, parameters or labels to D/G. It is richer input, not a third competing equal-input candidate or an information ceiling.

## Fixed material and observations

MATERIALS.md and generation-manifest.json fix eight development families: BWV773/775/778/781, isolated-track indices24–35, and four new seeded motifs. Previously exposed development works are not unseen-work validation. Historical evaluation material is not accessed for development. No replacement sampling is permitted.

Each family plans unchanged, transposed, uniformly stretched, inventory/rhythm foil and a near foil with an observed changed event. Source3s, eight intervening4s figures, last2s observed query; shifts−5,−2,+2,+5 and scales0.8/1.25 balanced within strata. Construction checks, seeds, foil and interference rules are fixed independently of matcher scores. The pitch-only duplicate-window guard stopped the sole construction attempt after35 sessions. No input was selected away and no partial rate panel was run.

Intended readouts per method: three positive cells × three history modes × eight families + two foils × eight families =88. D/G/exact total264. The eight separate diagnostic cases would add24; they were not constructed or run. Their planned paired worlds are deliberately constructed origin collisions, not evidence of an ambiguity in the musical families.

One-second arrivals carry10 rows and become available only at the unit end. A4-unit recent store and at most60 persistent units remain explicit. Each method/control runs in a fresh guarded child; recent/source-removal controls destructively delete records before deriving state. Whole source-overlapping units are selected for removal by evaluator labels; no true source interval enters candidate search. Derived matching state is per-call scratch, discarded at process exit. Predictor-accessible stored arrays and packet/concatenation buffers are counted against8MiB; scratch/RSS is reported separately. This is clean-observation simulation, not measured audio latency or raw-audio eviction.

The child logs prediction completion; the parent records response receipt after serialization as the actual output-availability upper bound. A separately named simulated bound adds readout roundtrip to the final completed-unit time. Ordinary array inputs do not carry generator IDs, scores, source boundaries or transformation labels. The Python file/network guard is API isolation, not an adversarial operating-system sandbox.

## Qualification and intended scoring

At most32 tiny non-musical probes were allowed. The29-call ledger retains one failed test-fixture attempt and its correction;28 calls passed and all final23 mathematical checks plus5 process checks passed. No candidate implementation was changed after these checks. The musical construction then failed. No scientific scoring, diagnostic-suite run or independently counted extra matcher verification followed.

The unexecuted musical criteria are: accepted correct source≥7/8 separately for unchanged/transposed/stretched; accepted correct source and exact shift≥7/8 in each cell; accepted correct source and scale within10% relative error≥7/8 in each cell; accepted foils≤1/16; source-removal substitutes≤2/24; recent-only accepted returns≤2/24; all evidence/access/removal/budget checks. Conditional estimation, joint success, localization, per-family/stratum outcomes and uncertainty must be reported separately. Rejection stays in each denominator. All fixed families remain included. Neither a richer-score win nor an aggregate score may conceal a failed capability.

Authorized A selects an adequate equal-input diagnostic (D if both qualify). B applies only when neither qualifies and a checkable observational ambiguity supports a narrowly specified contract revision. C withholds qualification when neither qualifies without such a witness. **This attempt is INVALID construction instead**: no A/B/C decision, no result estimates and no theoretical impossibility claim.

## Freeze, resource and stop policy

Hard limits:400 total method calls/probes,7200 aggregate local seconds including preparation/validation/publication,512MiB new artifacts,$0. No audio/model sweep, MERT operation, learned controller, additional download of musical data, exposed-panel retuning or automatic successor. Preparation code, fixed choices, saved inputs, ledgers and failure evidence are hashed in the snapshot manifest. No preregistration receipt was posted because the complete panel was not constructed. No musical execution SHA exists; the preparation snapshot SHA is identified honestly in publication.json.

Publish the complete invalid attempt with rootPROJECT_STATE.md, code, partial inputs, qualification outputs and exact limitations. Stop at awaiting-review. PM owns the next bounded disposition; any failure-evidence recovery or generator correction needs that disposition, not routine Brian approval.
