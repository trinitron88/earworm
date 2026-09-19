# Experiment 08 calibration audit: saved-input blocker

**Status: full margin audit blocked; partial evidence checks complete.**

Inspected snapshot: `44349be60642d25ea206b05831a98c362234a25f` on PR #2.
This continues the [PM handoff](https://github.com/trinitron88/earworm/pull/2#issuecomment-5740577316) and [review 5255130712](https://github.com/trinitron88/earworm/pull/2#pullrequestreview-5255130712). No existing calibration-audit output was present in the inspected branch or accessible local workspace. Another worker's unpublished local state is not accessible here.

The actual fitted model and decision threshold remain frozen. The threshold is **3.6264131202365606**. No alternate threshold was calculated, and the requested leave-one-calibration-group-out sensitivity remains incomplete.

## Missing evidence

The complete Git tree contains neither of these runner-produced files. `PROJECT_STATE.md` explicitly records omission of the development/held-out alignment tables.

| Missing saved input | Calculation blocked |
|---|---|
| `work/accounts_results/development_pairs.json` | Calibration candidate scores/evidence for groups e04–e07; four leave-one-group-out diagnostic thresholds and held-out calibration-group results |
| `work/accounts_results/held_out_pairs.json` | True-source score and maximum absent-history score, grouped by length and transformation, for the 576 held-out queries |

The pair tables store candidate evidence features; the unchanged `score()` function and frozen configuration map them to support logits. An existing equivalent score export would also suffice if it preserves every relevant candidate and the query/group/split/length/family/source and history membership identifiers. Generation metadata already exists in `work/accounts_stimuli/manifest.json`; it cannot supply acoustic scores.

`primary_trials.csv` records accepted handles and decisions, not support scores. The frozen calibration record gives 37 correct singleton retrievals and one false acceptance across 120 positive and 120 negative histories; these totals do not determine the thresholds for three-group subsets. The four report examples and emitted replay candidates cannot provide complete absent-history candidate distributions. Regeneration was not attempted.

## Observations supported by available artifacts

The supplied script checked all 2,304 primary rows (576 queries × four readers), reconciled method/length/family counts to the saved summary, and verified 11 input Git blob identities plus applicable original SHA-256 records. This is verification of saved artifacts, not a reproduction of the experiment.

| Phrase length | Accepted correct / queries | Accepted plus strict recovery |
|---|---:|---:|
| 4 | 32/144 | 32/144 |
| 6 | 68/144 | 60/144 |
| 8 | 32/144 | 32/144 |
| 10 | 32/144 | 32/144 |

Overall, accepted correct retrieval remains 164/576 versus the old reader's 198/576, with zero observed absent-history false acceptances for both. The saved post-hoc diagnostics total 553 uniquely correct first rankings. These rankings were not recomputed from candidate scores here. Family counts are in `evidence_tables.json`; full numerical margin distributions are unavailable.

Two existing, selected examples expose a very small positive margin:

| Query | Saved true-source logit | Logit minus frozen threshold |
|---|---:|---:|
| `e09_query_a_delete_rest` | 3.6266266302486665 | +0.0002135100121058997 |
| `e09_query_a_weak_present` | 3.6266266302486665 | +0.0002135100121058997 |

Both examples are from the same six-event group and have no saved absent-history scores in this export. They are illustrative, correlated cases, not estimates of overall margin size or false-acceptance risk. The two rejected report examples have no emitted support logits; their saved true-reference features were not rescored for this limited blocker check. Missing margins are recorded as null, never zero.

## Hypotheses and unresolved questions

The examples show that two accepted cases lie close to the current boundary. They do not show that changing the boundary is safe. Calibration coverage, feature treatment, acoustic group differences, and their interactions remain plausible explanations for length dependence. The degree of score overlap and leave-one-group-out threshold stability cannot be determined with the published evidence. Each calibration length has only one group, so even a future leave-one-group-out diagnostic would remove that length at the same time as that group.

## One bounded next action

Ask the original worker to publish a compact export of the **already saved** calibration and held-out candidate evidence/scores, with history membership, query metadata, and source-file hashes, into this audit directory. If those saved originals no longer exist, retain the blocker. This recommendation does not authorize regeneration or a new experiment.

## Check the partial calculations

The analysis script uses only Node.js built-ins and reads existing files. From a checkout of this published snapshot, choose a new empty output directory outside the checkout:

```sh
node review/experiment08/calibration-audit/check_saved_evidence.mjs --root . --out /tmp/earworm-audit-check-UNIQUE
```

Compare the generated `evidence_tables.json` and `verified_inputs.json` byte-for-byte with the copies here. Input paths, Git blob IDs, SHA-256 hashes, the original reviewed commit, and the complete inspected file inventory are recorded in `input_identifiers.json`, `verified_inputs.json`, and `source_inventory.json`. `CHECKSUMS.sha256` covers this audit package separately from original provenance.

The reviewed SHA identifies a publication snapshot. The original execution revision remains unrecorded; its source-hash provenance is preserved. All original experiment artifacts are unchanged. Publication stops at the `awaiting-review` checkpoint; no later recommendation is executed.

PR #2 is the shared operational instruction channel. The existing PM summary and [local-worker poll setup request](https://github.com/trinitron88/earworm/pull/2#issuecomment-5740638506) were read before this handoff. The local poll is requested but unverified; this publication neither installs it nor duplicates or changes the existing reviewer task. The export above remains a recommendation, distinct from Brian's authorization to perform this saved-data audit and publish a blocker if inputs are missing.
