# Experiment 08 review request and event-trigger test

## Purpose

Brian requested an end-to-end test of the existing Review Earworm Snapshots task. This isolated branch adds only this review-request note. It does not change experiment code, protocols, frozen evaluation rules, saved results, or the main branch. It does not launch or authorize an experiment or authorize additional spending.

## Snapshot provenance

All experiment artifacts are inherited unchanged from upload commit `06fe4470d64b0a1c00f3e65b7701a393af9a43d8`. The pull request's exact head commit will identify the review snapshot, including this note. Neither that head commit nor the upload commit is the original execution revision: PROJECT_STATE.md records that the original run was not made in a Git checkout. Retain that distinction and inspect the recorded source hashes.

This note is new review metadata, not part of the original experimental provenance manifest or checksummed artifact set. Do not modify those original records merely to include it.

## Review scope

Review the full Experiment 08 snapshot at the exact PR head, not just this note's diff. Start with:

- PROJECT_STATE.md
- work/accounts_results/protocol.json
- work/accounts_results/frozen_config.json
- work/accounts_reader.py
- work/accounts_experiment.py
- work/accounts_results/summary.json
- review/experiment08/primary_trials.csv
- review/experiment08/control_summary.csv
- work/accounts_results/posthoc_diagnostics.json
- work/accounts_results/metric_definition_note.json
- work/accounts_results/audit.json
- outputs/experiment08-milestone.md
- REVIEW_SNAPSHOT_MANIFEST.json and SHA256SUMS

Follow relevant implementation and evidence references as needed. Distinguish accepted retrieval from ranking, oracle diagnostics, and uncertainty about alteration causes. Distinguish directly inspected evidence from unverified reported claims. Do not execute reproduction commands as part of this read-only review.

## Observable test outcome

Adding the `earworm-review-ready` label is the readiness signal. Success requires the existing event-triggered task, rather than a manually posted review, to inspect the snapshot and post one evidence-grounded review identifying its exact head SHA, with exactly one bounded recommended next action, and summarize to the task's originating conversation.

Before posting, check prior reviews and discussion for a durable completed-review marker for that exact head SHA. This request is NOT such a marker: no scientific review has been completed by creating it. Preserve the task's deduplication and no-merge/no-code-change/no-experiment/no-spending boundaries. Do not treat a recommendation as permission for the worker to start the next experiment.

If the trigger does not run, report the test as unverified; do not replace it with polling or pretend a manual review proves event delivery. Leave this branch and pull request unmerged for inspection.

## Worker handoff test — 2026-09-19T08:35:19Z

The experiment artifacts remain unchanged. This commit appends only this worker handoff test note.

The reviewer must resolve PR #2's current head SHA from GitHub at review time and identify that exact revision in any review, rather than relying on an earlier SHA in the request. This note is not a completed review and does not authorize another experiment or spending.

## Calibration-audit handoff — 2026-09-19

The PM assignment and review 5255130712 were followed using the existing snapshot. The complete calibration-margin audit is **blocked by unavailable saved development and held-out candidate pair tables**. No experiment was rerun to recreate them. The publication contains a blocker report, checked partial evidence, and a reproducible saved-artifact check script.

Review this audit package at the current PR head:

- `review/experiment08/calibration-audit/REPORT.md`
- `review/experiment08/calibration-audit/evidence_tables.json`
- `review/experiment08/calibration-audit/check_saved_evidence.mjs`
- `review/experiment08/calibration-audit/input_identifiers.json`
- `review/experiment08/calibration-audit/verified_inputs.json`
- `review/experiment08/calibration-audit/source_inventory.json`
- `review/experiment08/calibration-audit/CHECKSUMS.sha256`
- `review/experiment08/calibration-audit/checkpoint.json`

The original experiment artifacts, model, threshold, and provenance records are unchanged. This is an `awaiting-review` checkpoint with a blocked audit, not a completed margin/sensitivity analysis. The report proposes one bounded next action only. Do not execute it automatically, launch Experiment 09, regenerate audio, refit models, change thresholds, merge, or authorize spending. Review the new head SHA once under the existing task; retain the prior completed-review marker for its original SHA.

## Saved-evidence audit completion — 2026-09-19T09:55:13.723440+00:00

The original local worker recovered the already saved candidate evidence and completed the existing authorized margin/sensitivity audit. This supersedes the prior missing-input status; the previous blocker package remains unchanged. The original experiment was not rerun, and its code, protocol, model, operational threshold, results, and provenance remain unchanged.

Review these new artifacts at the exact current PR head:

- `review/experiment08/calibration-audit/completion-20260919/REPORT.md`
- `review/experiment08/calibration-audit/completion-20260919/candidate_evidence.jsonl`
- `review/experiment08/calibration-audit/completion-20260919/input_identifiers.json`
- `review/experiment08/calibration-audit/completion-20260919/analyze_saved_evidence.py`
- `review/experiment08/calibration-audit/completion-20260919/export_saved_evidence.py`
- `review/experiment08/calibration-audit/completion-20260919/verify_audit.py`
- `review/experiment08/calibration-audit/completion-20260919/results/summary.json`
- `review/experiment08/calibration-audit/completion-20260919/results/query_margins.csv`
- `review/experiment08/calibration-audit/completion-20260919/results/candidate_scores.csv`
- `review/experiment08/calibration-audit/completion-20260919/results/stratified_margins.json`
- `review/experiment08/calibration-audit/completion-20260919/results/calibration_sensitivity.json`
- `review/experiment08/calibration-audit/completion-20260919/results/feature_contributions.csv`
- `review/experiment08/calibration-audit/completion-20260919/validation.json`
- `review/experiment08/calibration-audit/completion-20260919/checkpoint.json`
- `review/experiment08/calibration-audit/completion-20260919/CHECKSUMS.sha256`

The saved-data audit reproduces 553/576 uniquely correct first rankings, 164/576 correct acceptances, and zero observed held-out absent-history false acceptances. Omitting the sole six-event calibration group changes the diagnostic threshold and yields 6/30 false acceptances on that omitted group. Tiny score margins limit robustness claims. All alternative thresholds are calibration-only diagnostics; none replaces the frozen threshold.

Native local worker poll `earworm-worker-poll` is registered for 30-minute continuations in the existing Project Earworm conversation. This registration does not expand scientific authorization. The event-triggered reviewer is unchanged. Publish this complete snapshot once, save awaiting-review state, and stop; the report's one next-action proposal is not executed.
