# Same support vector, different retained accounts

**All 68 selected source/candidate pairs have identical twelve-feature support vectors, yet differ in the inspected saved acoustic/path fields.** The differences include timing transformations and the pitch, time or ordering of events expected from memory. They do not establish which memory the current sound identifies: the matched query evidence fits both accounts within the frozen scoring deadzones.

This completes `earworm-equal-vector-alignments-v1`, authorized by [comment 5744506474](https://github.com/trinitron88/earworm/pull/2#issuecomment-5744506474) and continued by [5744608819](https://github.com/trinitron88/earworm/pull/2#issuecomment-5744608819). Base main: `536f314b10b8d1d4a0cbb14a92caef9616157b47`. This is saved-evidence inspection, not an experiment, new alignment search, or changed scoring rule.

## Complete scoped inventory

The selection is exactly the 17 all-12-equal queries and all 68 maximum pairs in the [merged census](../heldout-feature-prevalence/results/maximum_pair_census.csv). Source-row numbers and query/source/candidate IDs are recorded in `saved_inputs.json`; identities route evaluation only.

| Item | Accounted for | Missing |
|---|---:|---:|
| Queries | 17 | 0 |
| Exact maximum pairs | 68 | 0 |
| Distinct query/reference evidence records | 85 = 17 true + 68 competitors | 0 |
| Saved best and retained alternative paths | 112 = 85 best + 27 alternatives | 0 |
| Cached acoustic descriptions | 52 | 0 |

Seven queries are `delete_two` (30 pairs); ten are `merged` (38 pairs). These selected cases come from six phrase groups. They are correlated cases selected for equal support, not a population sample. Every query and pair has an available status and checkable evidence in [inventory.json](inventory.json), [query_summary.csv](results/query_summary.csv), and [pair_comparisons.csv](results/pair_comparisons.csv).

The export contains the complete saved evidence records for those 85 comparisons and six typed event arrays from the 52 caches: onset, offset, pitch, pitch span, phase fraction and bend peak. It excludes unscoped candidates, waveforms and frame streams. Cached-description digests match the original extraction timing records; the original held-out pair-table hash matches the preceding audit. See [input identifiers](input_identifiers.json). Publication commits are not original execution revisions.

## What is being compared

Best paths are compared at their matched **actual onsets in the same query**. Reference-local indices are reported for traceability but are excluded, along with opaque IDs, from the acoustic comparison signatures. Those signatures contain measured reference/query event values, saved global transforms and ordered residuals, and the pitch/time hypotheses for missing or inserted events.

For a saved transform, mapped onset is `scale × reference onset + offset`; mapped pitch is `reference pitch + shift`. Missing-event lists are compared in chronological order. This compares the two accounts' expectations; it does not assert that their missing events have a common physical identity, or that the query contains those notes. Applying the saved transform to offsets gives expected interval endpoints, not a measured query duration.

All equality statements below use exact numeric equality. We report magnitudes so microscopic differences cannot masquerade as established musical distinctions. The original 0.05-semitone pitch and 0.005-second timing deadzones remain unchanged; no perceptual tolerance or new retrieval rule is introduced.

## Differences and apparent equalities

Counts below are **pairs out of 68**, not independent queries.

| Inspected property of the best paths | Exactly equal | Different |
|---|---:|---:|
| Matched query onset anchors | 68 | 0 |
| Global pitch shift, timing scale and offset together | 7 | 61 |
| All inspected matched-event acoustic fields | 6 | 62 |
| Ordered missing-event acoustic hypotheses | 0 | 68 |
| Missing-event placement relative to matched query anchors | 10 | 58 |
| All inspected best-path acoustic fields together | 0 | 68 |

The global pitch shift differs in 14 pairs, timing scale in 57, and timing offset in 58. Candidate timing scales range from about **0.3313 to 3.0061**. These are distinct retained descriptions of transformation; they are not automatically evidence against musical identity or support for the true source.

Matched reference onset intervals differ in 57 pairs, by up to **0.331 seconds**. Matched pitch intervals are exactly equal in 53 pairs; the largest difference in the other 15 is only **0.0003267 semitones**. All 85 best records have zero mean pitch loss and zero mean timing loss. Their maximum absolute saved pitch residual is **0.0001634 semitones**, and maximum timing residual is **2.23e−16 seconds**, both inside the original deadzones. Tiny nonzero residuals are therefore not treated as evidence that a musical distinction has been resolved.

**Fifteen of the 17 queries have only two eligible events.** The other two have four and six. With two matched onsets, a free timing scale and offset can fit those two times almost exactly; the residual summary does not report how much temporal transformation was needed. The saved path still retains that transformation.

The six pairs with exactly equal inspected matched-event fields still have different missing-event hypotheses. This is a useful boundary: memory preserves different expectations even where these inspected matched observations do not distinguish them. All 17 queries remain rejected under the frozen threshold; no retrieval improvement is claimed.

## Two concrete comparisons

**A short heard fragment, different temporal accounts.** In `e08_query_a_delete_two`, the query's matched events arrive at approximately **0.134 s and 0.299 s**. The true reference matches events at those same times, with scale 1 and offset 0, and expects its two unmatched events later, around **0.464 s and 0.629 s**. The tied alternate reference matches events originally at **0.134 s and 0.629 s**, using scale **0.3333333** and offset **0.0893333 s**. Its two unmatched events are then expected between the heard anchors, around **0.189 s and 0.244 s**. Both paths fit the matched pitch relationship and obtain the same support vector. The difference is a temporal account expressed in seconds, not merely “reference indices 1 versus 3.”

**The matched observations agree, but the remembered interior order differs.** In `e21_query_a_merged`, the true source and `e21_distractor_3` have exactly equal inspected matched-event fields and identical global transforms. Their two unmatched reference events have opposite low–high versus high–low pitch order, about **16 semitones apart**, at roughly the same interval in the phrase. The support vector retains the missing fraction but not that ordered interior content. This is a difference between remembered accounts, not proof that the query audibly selects one of them.

The measured query also retains an event in that region which lies outside its saved eligible event set. More generally, **all ten selected `merged` queries retain one such excluded cached event**. Each has a saved pitch span above the frozen 150-cent gate (approximately **300.8–1154.7 cents**), which is sufficient for exclusion under the recorded rule. We reconstructed membership from the saved matched/inserted sets; no detector or filter was rerun. The coarse event statistics alone do not establish whether useful pitch order survives inside those intervals.

## Retained alternatives

All **27 stored alternatives** were included; 24 of the 85 records retain alternatives, including three true-source records. The complete retained acoustic-path multisets differ in every selected source/candidate pair. In 46 pairs neither side has an alternative; their empty alternative-only lists are equal, which is not agreement between their best accounts. In the remaining 22, the inspected alternative-only multisets differ.

This is a comparison of already-retained paths, not an exhaustive ambiguity analysis. The original search/retention limits still apply. [Saved paths](results/saved_paths.csv), [matched correspondences](results/matched_correspondences.csv), [missing-event hypotheses](results/missing_event_hypotheses.csv), and [inserted events](results/inserted_query_events.json) account for every retained path. [Cached events](results/cached_events.csv) include events excluded from the saved eligible sets.

## What this establishes—and what remains open

The retained representation is richer than the scalar support input: it keeps transformations, ordered correspondences, missing-event expectations and some event observations that the twelve features omit or compress. Equal support vectors are not evidence that this richer state was erased.

The audit does not show that every retained difference matters for identity, that the true source is audibly recoverable, or that rejection is wrong. Missing-event expectations are supplied by the competing memories; they cannot silently replace observations. Some ambiguity may be warranted by the small surviving fragment. Construction labels locate the true source for evaluation but do not resolve that perceptual question.

**One proposed next action, not executed:** inspect the already-saved frame timelines inside the ten excluded `merged` query events, using their fixed cached onset/offset bounds, to determine what ordered pitch or energy evidence remains there. Keep observations separate from either memory's expected notes; do not extract new features, search paths, fit a rule, or choose a retrieval winner. Missing cached fields should be reported rather than regenerated. Await explicit reviewer authorization.

## Verification and reproduction

All scoped source records and typed event arrays match their saved originals. The selected 68 pairs map exactly to the frozen census; all twelve-feature equalities and frozen scores reconcile. Reconstructing saved pitch/timing residuals, loss arithmetic and best-path features gives **zero discrepancy** across this export. A separate standard-library verifier independently checks scope, all 112 paths, and pair comparisons without importing the analysis or experiment modules. The 1e−12 verification tolerance is for arithmetic checking only.

The analysis writes nine deterministic result files. Validation records their byte-identical clean reproduction, original-input preservation and independent checks in [validation.json](validation.json). From this directory, in the existing Python/NumPy environment:

```sh
python analyze_saved_alignments.py --out /tmp/earworm-alignment-audit-results
python verify_saved_alignment_audit.py --results /tmp/earworm-alignment-audit-results
```

Use a new or empty output directory. `export_saved_alignments.py` additionally requires the original local saved pair table and caches, which are not fully included in the repository. Its scoped export is provided here; neither analysis command regenerates omitted inputs. Original experiment artifacts and all prior audit packages remain unchanged. No audio/model pipeline, training, new experiment, changed threshold, spending or worker merge occurred.
