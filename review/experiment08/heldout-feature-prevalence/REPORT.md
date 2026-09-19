# How often do distinct candidates retain the same support features?

**The ten-feature agreement pattern occurs in 121/576 held-out queries (21.0%), across 9/16 phrase groups. It is broader than the selected e21 example, but it does not account for most retrieval rejections.** This is a descriptive census of existing saved evidence, with the model and operational threshold unchanged.

Assignment: `earworm-heldout-feature-prevalence-v1`, [PR #2 comment 5744179177](https://github.com/trinitron88/earworm/pull/2#issuecomment-5744179177). Base main: `1c695ffc33e00f239ac5b070696b8b1a2121ac59`, containing the reviewed [matched-pair audit](../matched-pair-audit-e05-e21/REPORT.md). No new experiment, extraction, alignment search, training, or spending.

## Exact definitions and denominators

For each of the **576 queries**, examine its nine-candidate absent history, including the alternate reference. Retain **every exact score maximum**, then compare each maximum's saved vector with the true source's vector. This yields **632 pairs**: 18 queries have tied maxima. The alternate reference is among the maxima for 48 queries.

The four mutually exclusive pair categories are:

- **All 12 equal:** both records available; all twelve feature values exactly equal.
- **Cost/timing only:** both available; the other ten features exactly equal, with `cost` and/or `mean_timing_loss` different.
- **Other differences:** both available; at least one of the other ten differs.
- **Unavailable:** either record unavailable; its sentinel vector is not evidence of equality.

Equality means exact numeric comparison of the published feature values, without rounding or a tolerance. Query **any** counts a query once if at least one tied maximum has that category; query **all** requires every tied maximum to have it. Any-category columns can overlap in principle. Here every query's tied maxima belong to one category, so any and all counts coincide. All 632 comparisons have available evidence.

| Category | Pairs / 632 | Queries: any / 576 | Queries: all / 576 | True singleton | No candidate accepted |
|---|---:|---:|---:|---:|---:|
| All 12 equal | 68 | 17 | 17 | 0 | 17 |
| Cost/timing only | 104 | 104 | 104 | 4 | 100 |
| Other differences | 460 | 455 | 455 | 160 | 295 |
| Unavailable | 0 | 0 | 0 | 0 | 0 |
| **Total** | **632** | **576** | **576** | **164** | **412** |

There are **zero wrong singletons, zero multiple-candidate outcomes, and zero observed absent-history false acceptances**. These reproduce the frozen source-present and source-absent decisions. The 68 all-equal pairs belong to only 17 queries: treating pairs as independent queries would inflate prevalence.

## Where the pattern occurs

“Ten equal” below combines all-12-equal and cost/timing-only. Each length has four groups and 144 queries.

| Phrase length | All 12 equal | Cost/timing only | Ten equal / 144 | True singletons / 144 |
|---|---:|---:|---:|---:|
| 4 | 15 | 58 | 73 (50.7%) | 32 |
| 6 | 1 | 14 | 15 (10.4%) | 68 |
| 8 | 1 | 20 | 21 (14.6%) | 32 |
| 10 | 0 | 12 | 12 (8.3%) | 32 |

Group counts for ten-equal queries, each out of 36: e08 **23**, e09 **1**, e10 **0**, e11 **0**, e12 **12**, e13 **1**, e14 **21**, e15 **0**, e16 **14**, e17 **0**, e18 **0**, e19 **0**, e20 **24**, e21 **13**, e22 **0**, e23 **12**. Length and phrase-group structure are not independently randomized here; this concentration does not establish a causal length effect.

Each transformation family has 32 queries. These are evaluation labels, not inputs to the scorer.

| Family | All 12 equal | Cost/timing only | True singletons / 32 |
|---|---:|---:|---:|
| delete_closed | 0 | 10 | 4 |
| delete_detune | 0 | 7 | 0 |
| delete_insert | 0 | 10 | 0 |
| delete_rest | 0 | 10 | 8 |
| delete_timing | 0 | 10 | 8 |
| delete_transpose | 0 | 10 | 8 |
| delete_two | 7 | 4 | 0 |
| detune | 0 | 0 | 0 |
| exact | 0 | 0 | 32 |
| insert | 0 | 0 | 0 |
| legitimate_rest | 0 | 0 | 32 |
| mask_absent | 0 | 10 | 0 |
| mask_present | 0 | 10 | 0 |
| merged | 10 | 4 | 0 |
| substitute | 0 | 9 | 0 |
| timing | 0 | 0 | 32 |
| transpose | 0 | 0 | 32 |
| weak_present | 0 | 10 | 8 |

The full [stratified table](results/stratified_counts.csv) includes pair counts, query any/all counts, availability, ties, outcomes and margins by group, length, family, length × family, and group × length × family. Each partition independently reconciles to the overall counts.

## Frozen scores, margins, and prior cases

Threshold: **3.6264131202365606**. Acceptance remains exact `score >= threshold`. A margin is score minus this threshold; a source advantage is source score minus maximum absent-history score.

- The 17 all-equal queries have exactly zero source advantage. Their source and absent margins range from **−3.431084153 to −1.712718167**; all are rejected.
- The 104 cost/timing-only queries have source advantages from **−0.000156226 to +0.000559929**, median **+0.000241081**. Four are accepted and 100 rejected. The four accepted variants all belong to source a in group e21; they are not four independent phrase groups.
- Across all 576 queries, the largest absent margin is **−1.2761520000736937e−6**. Zero false acceptances in this saved set does not establish a population error rate or a robust numerical margin.
- The prior strict **absolute score difference < 1e−9** diagnostic identifies 18 source/absent near ties: the 17 all-equal queries and `e12_query_b_delete_closed` (gap **−6.180478351325291e−11**). Separately, 19 queries have additional absent candidates within that diagnostic range of the maximum. These candidates do not enter the exact-max pair counts unless exactly tied.

The earlier held-out cases reconcile exactly: e21-a `delete_closed` is cost/timing-only, with source advantage **8.923636016788805e−7** and source margin **−3.8378839839481316e−7**. e21-b is “other differences,” with source advantage **4.671581424778927** and source margin **−8.914790843306264e−7**. Both reject all candidates. Their saved vectors, histories, maximum IDs, scores and margins match the merged audit.

## Interpretation and limits

At the level of these twelve support features, the 17 all-equal queries contain no distinction between the true source and the retained competing maxima. Any deterministic readout using only those identical vectors must give them identical outputs. This says nothing about equality of the underlying acoustic descriptions, ordered alignment paths, or human perceptual identity.

The cost/timing-only pattern is a recurring limitation of this saved representation, concentrated in particular groups and transformations. Its category definition does **not** establish that every cost difference is caused by timing, or that the two terms always encode one independent observation. That relationship was checked only for the earlier selected cases.

The combined pattern accompanies **117/412 rejections (28.4%)**; **295/412 (71.6%)** occur with other feature differences. It is therefore one bounded issue rather than a complete explanation of rejection. These are correlated synthetic variants and post-hoc descriptive counts; no population confidence intervals, causal claims, or perceptual judgments are inferred.

## Evidence and reproduction

Inputs are the previously published compact export, frozen configuration, archived scores/margins and decisions, and merged e21 evidence. Original omitted pair files and acoustic caches were not read or regenerated. [Input identifiers](results/input_identifiers.json) record repository paths, sizes and hashes; generator metadata is used only for evaluation and stratification.

The audit verified all **5,760 held-out candidate scores exactly** against the earlier NumPy arithmetic and all **576 present/absent decisions** against primary trials. Independent scalar summation differs by at most **3.553e−15**. Its 1e−12 verification tolerance does not change decisions, exact maxima, or feature categories. A separate standard-library verifier checks all 632 maxima/pairs and category assignments from the published inputs; all five stratification partitions reconcile. Six output files reproduce byte-for-byte. See [validation.json](validation.json).

From this directory, using the existing Python/NumPy environment:

```sh
python analyze_prevalence.py --out /tmp/earworm-prevalence-results
python verify_census.py --results /tmp/earworm-prevalence-results
```

Use a new or empty output directory. [Per-query census](results/query_census.csv), [all maximum pairs](results/maximum_pair_census.csv), [category outcomes and margins](results/category_outcomes.csv), and [summary](results/summary.json) contain the checkable results. Prior artifacts are preserved.

**One proposed subsequent action, not executed:** inspect the already-saved alignment correspondences for the 17 all-equal queries and their 68 maximum pairs to determine whether ordered relationships distinguish them despite identical support vectors. This could separate distinctions lost during aggregation from ambiguity already present in the retained alignment evidence. If essential saved correspondences are absent, document that gap without regeneration. Await an explicit reviewer assignment.
