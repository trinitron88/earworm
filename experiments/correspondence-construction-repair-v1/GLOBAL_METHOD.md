# Candidate G: global correspondence with explicit observation uncertainty

This is the fixed development candidate for `earworm-correspondence-reference-choice-v1`, paired with an unchanged historical D. Neither G nor G-exact-score is an information upper bound. Their implementation and declared observation model can fail independently of the information in their inputs. No acoustic route is run here.

## Attribution and adaptation

Primary specification: Kjell Lemström (2010), *Transposition and Time-Scale Invariant Geometric Music Retrieval*, S1, Section 3.1, [institutional full text](https://helda.helsinki.fi/server/api/core/bitstreams/3ee07ff3-78ba-44a6-81d0-9c2b8ab7dbaf/content), [DOI](https://doi.org/10.1007/978-3-642-12476-1_12). S1 connects every query point through one positive time scale and pitch translation; consecutive query correspondences must agree on that scale. G borrows that global affine correspondence model. It exhaustively enumerates possible correspondences rather than implementing the paper's priority-queue acceleration. The scale reported here maps **history to query**; this direction is explicit throughout.

The paper does not supply or validate Earworm's sampled-run representation, interval feasibility, negative-evidence verification, clipping, abstention, or scoring. Those are adaptations described below. In particular, its point-set formulation can allow extra database notes. Earworm's full-consistency verifier instead requires consecutive matching run evidence, including silence, and forbids skipping a contradictory run. This additional restriction is part of the tested implementation, not a theorem about auditory information.

## Input interface and availability

`predict(state, exact=False)` returns ordinary JSON-compatible objects. The equal-observation G accepts only these keys:

- `t`: strictly increasing sample centers in seconds.
- `rms`: the historical query-selection occupancy cue (score occupancy in this clean simulation, not measured acoustic RMS).
- `unit`: the completed one-second unit containing each sample.
- `clean`: lossless N-by-129 one-hot rows; columns 0–127 are absolute MIDI pitch and column 128 is silence.
- Optional `available_at`: when present, must equal `unit + 1` for every row.

Samples must lie within their stated units. G neither changes the arrays nor stores a cache between calls. Unknown keys cause `ValueError`; in particular the equal-observation call refuses exact events, score boundaries, identifiers, or generator metadata. Inputs must be finite and monophonic. Invalid input or an internal arithmetic contradiction is an **implementation/input INVALID**, not an ordinary refused match.

The query selection copies the historical rule: take the last row whose occupancy cue exceeds `1e-4`, then every available row in the preceding two-second window, with the historical endpoint arithmetic. At least 12 rows are required, as in D. The complete panel normally provides 20. No event count, missing-note count, intended source, transform, or original phrase boundary is supplied. Query gaps exceeding `0.10001` seconds produce a refusal for missing support; they are not bridged or interpolated. Earlier history consists exclusively of rows from units strictly before the unit containing the first selected query row. G enumerates every surviving history component, separated at the same gap limit. A one-row component cannot cover a positive-duration query.

The verified time support is the closed interval between the first and last selected sample centers (normally 1.9 seconds). The historical displayed two-second bin support, including half a bin at each edge, is separately returned as `query_display_bin_support`; these outer half-bins do not become observations. G-exact-score uses the **same center-to-center support**. A selected occurrence's `start` and `end` refer to the mapped verified support, not an inferred onset/end of the complete stored phrase. Localization must be scored and reported separately from source identity.

## Sampled observation model

Within each intact history component, and within the query, construct maximal runs of identical pitch/silence labels. Preserve every original row ID in the run index. Adjacent observations of the same pitch remain one run: G does not invent repeated-note onsets. Silence is an explicit label, invariant under pitch translation.

For two adjacent centers with different labels, a transition lies in `(old_center, new_center]`. The left endpoint is excluded because the old label was observed there; the right endpoint belongs to the new label. The first and last run of an observed component are censored at its first/last center. They do not acquire a claimed onset or offset. No additional event between two equal labels is inferred. This is an explicit piecewise-constant, at-most-one-transition-between-different-adjacent-rows model, not a claim that the waveform or a score could not contain extra unobserved events.

For each integer pitch shift from -5 to +5, enumerate all consecutive history-run windows with exactly the query's run-label sequence after that shift. Runs containing silence require silence on both sides; pitched values never wrap into the silence column. Every window remains inside one retained component. Removal holes therefore cannot be crossed even when their two sides have matching pitch.

One transform is shared by the entire correspondence:

`query_time = scale * history_time + offset`

`query_pitch = history_pitch + shift`

with `scale` in `[0.65, 1.5]`. For each paired transition bracket, the transformed history bracket and query bracket must intersect with their correct open/closed endpoints. Additional inequalities require the mapped query support to remain inside the surviving component and its edge runs. All conditions are affine inequalities in `(scale, offset)`; exhaustive convex-polygon clipping gives the full feasible parameter region for that run correspondence. There is no scale grid, fitted timing allowance, threshold sweep, chosen source interval, or endpoint-span scale surrogate.

The model asks whether **there exists** a single latent sequence of transition times consistent with both sets of samples under that transform. Each transition gets its own witness within the intersecting brackets, while the scale and offset remain global. The brackets can leave a wide range: this is retained and reported rather than silently converted to exact timing knowledge.

## Verification and output

A candidate is admissible only if its parameter region is nonempty and a deterministic representative satisfies every constraint. The representative is the arithmetic mean of the distinct clipped-polygon vertices in local time coordinates. It is a reproducible reporting choice, not a learned parameter or musical preference. A transition witness uses the midpoint of its feasible intersection. Then the verifier independently visits **every available query row**, plus every historical row falling within the mapped query support, checking its label against the complete witnessed sequence. All query runs have correspondences. Skipped query rows/runs are zero; contradictions at this stage raise an arithmetic failure rather than being silently dropped.

Each output candidate contains:

- The complete run correspondence and original row IDs.
- The selected start/end/center, integer shift, scale (also `stretch` for interface compatibility), and global offset.
- Feasible scale, offset, start, and end ranges and the parameter polygon.
- Every inequality, whether strict, and its coordinate origins.
- A transition witness and the original brackets.
- Explicit verified query/history row IDs, verified run count, zero skipped evidence, and retained support.

The returned polygon and ranges describe the **closure** of the feasible set. A strict boundary may be an unattainable limit; the saved strict inequalities and interior representative distinguish this. `parameter_uncertain` is true when scale or offset spans more than arithmetic roundoff. Weakly constrained estimates remain estimates with ranges even if the occurrence is uniquely supported. A broad range is not hidden by a perfect identity score.

All fully consistent occurrence windows have equal evidence rank. Ordering by component, run range, and shift only makes the output deterministic. G returns **all** such windows. Exactly one window is accepted; multiple distinct run correspondences cause abstention, including overlapping but distinct occurrence explanations. No earliest-source rule, ad hoc merging, proximity to a true source, or preference for unchanged pitch/tempo resolves a tie. No match is an ordinary refusal. The rates must count refusal in the unconditional identity/transform denominator.

## Richer exact-score diagnostic

`predict(state, exact=True)` additionally requires `events` (N-by-3 `[on, off, MIDI]`) and `segments` (N-by-2 retained support intervals). Optional `event_left_clipped` / `event_right_clipped` vectors have one flag per event. Events are clipped to **merged contiguous retained support**, not independently to each one-second unit: unit boundaries must not manufacture new note onsets. No event may cross a removed support interval; removal must reconstruct the event state from surviving observations. Event times are permitted only within the same arrived retained support. IDs and labels are never accepted.

The implementation validates that events are positive-length, ordered, nonoverlapping, within support, and consistent with every received pitch/silence sample. It derives exact monophonic intervals and silence gaps restricted to the selected query and each history component. Genuine adjacent repeated notes retain their separate event boundaries, including when the pitch repeats. Component/query edges are censored: a clip does not become a known note onset. When the label changes exactly at the final support point, a zero-duration terminal run retains that point observation instead of discarding it.

The transform, shift/scale bounds, full-consistency verifier, exhaustive search, representative, and abstention rule are the same. Internal transition brackets collapse to exact times. Exact offsets and silence provide additional full-evidence constraints beyond the paper's note-onset pattern. The stronger observation interface may resolve sampling/repetition uncertainty and improve scale estimation; that is a **richer observation diagnostic**, not an equal-input victory and not evidence that an acoustic encoder failed. It is deliberately not a third competing route.

## Numerical and resource policy

Calculations use binary64. `64 * machine_epsilon * (1 + sum(abs(terms)))` is the fixed arithmetic allowance for comparisons and vertex deduplication. Strict inequalities require a margin larger than that allowance; near-zero-margin cases are conservatively rejected. This protects sampling semantics but can miss an extremely narrow mathematically feasible set. It is not a musical tolerance and is never fitted. Degenerate line/point polygons are retained for exact correspondences. An impossible row witness is recorded as INVALID and must not be repaired after panel exposure.

There is no filesystem/network/model access or persistent derived cache in this module. Arrays, run indexes, feasible polygons and witnesses exist only for one call. They are predictor scratch/output and must be included in the runner's resource accounting; the retained arrays remain counted as predictor-accessible persistent storage. The driver alone owns budget accounting, fixture invocation, fixed panel exposure, isolation, removal controls, output commitment, labels and scoring. This module has not been given labels or historical evaluation material.

No matcher/probe/panel invocation was performed by this implementation subagent. Only syntax compilation was run. The root worker owns all at-most-32 qualification probes and any subsequent frozen readouts. Qualification failures must be resolved before panel exposure within the same allowance, or checkpoint as required by the assignment.
