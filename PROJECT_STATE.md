# Project Earworm

Earworm investigates auditory representations and memory that can interpret present sound using an auditory past while preserving what was actually observed. The long-term goal is music listening and interpretation; current synthetic results do not establish human appreciation or perceptual identity.

## Current state

The controlled motif robustness assignment is complete and awaiting external review. **Branch C: repair the observation prerequisite before advancing acoustic complexity.** The unchanged simple relative retrieval reference and its allowed readout reparameterization both achieved 100% accuracy with matched rendering or duration changes, but 75% with timbre changes, below the frozen robustness criteria. The separate arrived-fundamental diagnostic reached 100%; its paired gain was 25 percentage points, 95% CI 8.3–41.7. Saved traces show octave errors in the acoustic anchor for overtone-rich current cues.

The simple retrieval mechanism remains the reference. Calibration improved proper scores without changing point decisions. No extractor repair has been implemented. Supplied note boundaries, synthetic monophonic tones and stipulated continuations remain substantial limitations.

- [Current report](experiments/controlled-motif-robustness-v1/REPORT.md)
- [Frozen protocol](experiments/controlled-motif-robustness-v1/protocol.json)
- [Decision and gates](experiments/controlled-motif-robustness-v1/results/heldout/decision.json)
- [Validation](experiments/controlled-motif-robustness-v1/validation/heldout.json)

## Preserved findings

PR #8's history-prediction study selected the simpler transformation-aware retrieval reference rather than adding a relational model. Its evidence and all earlier artifacts remain unchanged. Experiment 08 retained strong ranking (553/576 uniquely correct first) but low acceptance (164/576); subsequent saved-data audits distinguished ranking, evidence aggregation, eligibility and calibration. These correlated audits are not independent failures and do not justify a broad pivot.

- [History-prediction report](experiments/history-prediction-v1/REPORT.md)
- [Original E08 state](review/experiment08/original-snapshot-PROJECT_STATE.md)
- [Saved frame audit](review/experiment08/excluded-event-frame-timelines/REPORT.md)

## Next authorized action

Publish this complete successor snapshot and await review. After review, the PM may issue one explicit bounded roadmap assignment for an observation repair with fresh confirmatory groups. This result alone authorizes no follow-on execution. The previously deferred estimator-provenance audit remains deferred. No spending, MERT changes, natural-performance or polyphonic jump, worker merge, or automatic second study.

Every successor PR updates this living overview. Historical code, models, protocols, results and audit packages remain frozen.
