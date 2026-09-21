Preregistration: earworm-frame-lattice-validation-repair-v1

Authorized by comment 5754247055. Exact base: 9c468da5cebe513119320fac436cf28c3b9a0008. Frozen execution commit: 6303e0036069465d5b6cd67ab3d46975c0a70568.
Package: experiments/frame-lattice-validation-repair-v1/.

The ONE validation correction passed complete saved development/calibration checks: 76,416/25,888 lattice frames, zero RMS/spectral component error; 8,192/8,216 chained records; 10,560/8,000 reconstructed forecasts; 32 future probes and 8 save/restores each; all763 historical hashes unchanged. The four endpoint-only frames reconstruct with nonzero raw RMS, zero Hann power, denominator1e-20 and eight zero bands. No additional mismatch. Calibration's8,000 scores independently match <=4.45e-16. Original calibration outcome files remain byte-identical, including the historical invalid decision; new validation receipts supersede only the integrity finding.

Heldout remains unstarted and unexposed: no heldout directory/STARTED in old or new package. No audio replay, feature/model rerun, reselection, calibration fit or new preflight. Data directories and prior outcome files were copied exactly (reused_evidence.json and validation/preservation.json). f32 is unchanged. All scientific/runtime files and criteria are unchanged. Only verify.py changed. The unchanged broker retains its legacy PR15 Git path; freeze.files contains only byte-identical inputs verified at that path. All new-package code, including the changed validator, is separately bound to this execution commit and the broker's aggregate code hash before start.

Reserved execution: exactly24 groups fir-16..fir-39,576 streams, original seeds/manifest; no replacement. Same20 episode/control streams+4 probes/group, save/restore within existing probes. At most32 arrived chunks and2-second completed waveform units. No future metadata reaches the worker.

Cumulative ledger at preregistration:386 streams already consumed,576 remaining ->962 total. Prior compute1547.20676s; abandoned setup charged335s; resumed work conservatively charged elapsed time since03:33:15.156Z. Current total charge 2181.635s of7200s; reserved work must fit the remainder. Combined failed-prefix/PR15/continuation artifact limit2GiB. No spending. Any execution/validation mismatch stops; no retry/repair.

Frozen source/input hashes:
```json
{
  "files": {
    "trim_front.py": "a9a054457b6277ce6badfffe709382302181ea21744198e61bf47b4993fc5e8f",
    "worker.py": "3a3f5df381bfea212d8c7789a8d65357de88bf421754c0db8f7b8590cccfca02",
    "accepted_adapter.py": "fd7e8f88f29e2fa4bb71c14e6ca02c3f209595118f47971ba255ef06cf778747",
    "run.py": "beacbd6db357c11a653ae21339a295b32fe8f5bcf05b5cecd37096cff641f252",
    "historical_front.py": "433c0b89b184bb5d74da1bd307d45616f54e6da1d5dff8851e076bbfbc9ac483",
    "reference_model.py": "930d3ecc758704ad27941f1fe6b29041d7350814d27198437deedc422f1ddd70",
    "events.py": "0c15fd73847c5133d7b5a86b9c9ee005cc34a69592cdb57d35bda5b2cc363489",
    "scoring.py": "dc694c0cd3fe3bab74fb9fddb7fb6d1518ccf5ef09c01f0494b1672c2f63dbd8",
    "records.py": "0b4d3b458b48ceec2578e0238d8f771abcbe5c3e872e0586e6a463023d68c5fb",
    "validation_math.py": "a685fdacffe62131ee8d25ba2967372de50e36663f065fee9e166c9dbf6c7e2c",
    "aggregation_front.py": "3a78d91624637f7ab7dd814f2455d9746b49dbc21b76c0aa4e16701c86ff7805",
    "model.py": "4f90ffa69dbaa4055920f68048153f362fc11ab03709cfdbe398a5bbe9738a7e",
    "lattice_validation.py": "1a86bf4ab682f4269226c3f51fe19cb090e542ceac4b4fbed44efe9ff1b7b101",
    "stimuli.py": "72c7624fa42cd3b73080f483f7c7fb20c1d0d30300c46a4e2dd6bbd91daaf0ff",
    "select.py": "18b2e7c8281f388fc0be2f48417e7c176109663f3df9f139b7307c8daacb658f",
    "analyze.py": "13e2e2881edb679698ff02c418d78fa6bed78c1ba48624ea990e135d87835f38",
    "preflight.py": "b27501ececfaaf4915eebba25295a3f026584d92316803553fe493d0934a6bcb",
    "protocol.json": "84a5c84dbc5dd707ae860b25c2f35dc4f28b652da5616dcb507fc309bd4c919b",
    "initial_model.json": "47011bfa4a6db13868d0f7fbbe858fbbdf4462d6ab0aaf94077e5e65388da89b",
    "frozen_model.json": "57c013bd25d07914eed6c96c38ba69e24b678814f0b4bac9c2d283e69264979a",
    "reference_config.json": "2a8e2115572b25c75786b01eac5a6779e4fdd22e26a4a68c8313a4e4af1e80d6",
    "split_manifest.json": "d4680a6e0b7c92daca65af3a943af7bee0dede262fa7008058fa325fb7a88f5d",
    "excluded_prior_motifs.json": "dd67cc74027bae0d76ac352d94e53a6d22f88624072a9b21c2302c69d59fb948",
    "development_selection.json": "c96429c509c8305615a1c9e4dd426412407999df2e6628af97b27f6374630771",
    "preflight_result.json": "e82b1d458273ab3dce3550f65844ad5ecdd4288dc7d5aa5342dacc62022032ec"
  },
  "execution_code_sha256": "b4c1ea170e13ca8b3e9129d6c739cd47ab8049ee60fc60d299250f6fd82d23e9",
  "all_execution_sources": {
    "accepted_adapter.py": "fd7e8f88f29e2fa4bb71c14e6ca02c3f209595118f47971ba255ef06cf778747",
    "aggregation_front.py": "3a78d91624637f7ab7dd814f2455d9746b49dbc21b76c0aa4e16701c86ff7805",
    "analyze.py": "13e2e2881edb679698ff02c418d78fa6bed78c1ba48624ea990e135d87835f38",
    "events.py": "0c15fd73847c5133d7b5a86b9c9ee005cc34a69592cdb57d35bda5b2cc363489",
    "historical_front.py": "433c0b89b184bb5d74da1bd307d45616f54e6da1d5dff8851e076bbfbc9ac483",
    "lattice_validation.py": "1a86bf4ab682f4269226c3f51fe19cb090e542ceac4b4fbed44efe9ff1b7b101",
    "model.py": "4f90ffa69dbaa4055920f68048153f362fc11ab03709cfdbe398a5bbe9738a7e",
    "preflight.py": "b27501ececfaaf4915eebba25295a3f026584d92316803553fe493d0934a6bcb",
    "records.py": "0b4d3b458b48ceec2578e0238d8f771abcbe5c3e872e0586e6a463023d68c5fb",
    "reference_model.py": "930d3ecc758704ad27941f1fe6b29041d7350814d27198437deedc422f1ddd70",
    "run.py": "beacbd6db357c11a653ae21339a295b32fe8f5bcf05b5cecd37096cff641f252",
    "scoring.py": "dc694c0cd3fe3bab74fb9fddb7fb6d1518ccf5ef09c01f0494b1672c2f63dbd8",
    "select.py": "18b2e7c8281f388fc0be2f48417e7c176109663f3df9f139b7307c8daacb658f",
    "stimuli.py": "72c7624fa42cd3b73080f483f7c7fb20c1d0d30300c46a4e2dd6bbd91daaf0ff",
    "trim_front.py": "a9a054457b6277ce6badfffe709382302181ea21744198e61bf47b4993fc5e8f",
    "validation_math.py": "a685fdacffe62131ee8d25ba2967372de50e36663f065fee9e166c9dbf6c7e2c",
    "verify.py": "f503284936e29abe9862f5e5e9339d84302411904a33b9518ddfdf1ec16147d9",
    "worker.py": "3a3f5df381bfea212d8c7789a8d65357de88bf421754c0db8f7b8590cccfca02"
  },
  "validation_sources": {
    "validation/independent_scores.py": "31559c72fae8a441807072fa4830dcb68e6920ed1d6b96fa40a366b2d373d7da",
    "validation/preservation.py": "b6bc5e476d00d6e6b2945af9844c76e386f065178c2a3db6c2fa48c424d74794"
  },
  "continuation_protocol_sha256": "c1b1bd3c3ca1fc3c7d6ab6f5c941ae1a9f83ffc1137a935c91b45ce308a9510d",
  "assignment_sha256": "14b064adc193c701a4021ae4423baad915213c1643de1661659d3552f882644d",
  "reused_evidence_sha256": "745abe2ed496c24197bd56bd7d507f566af6c659a1111d8ab716ce2f94359e8b",
  "historical_manifest_sha256": "579048bc5168aafb9249a6a640cd717c4c64d08a24e6c65a16080124503b7f48",
  "frozen_at": "2026-09-21T03:37:08.574382+00:00",
  "legacy_broker_check": "Unchanged run.py verifies files against PR15 package at HEAD; all those entries are byte-identical. all_execution_sources separately binds corrected verify.py and every source in this new package to the new execution commit before starting. Its top-level aggregate is also enforced by run.py. No runtime edit."
}
```

Original scientific rules, acceptance gates, branch precedence, bootstrap, clocks, state accounting and limitations (byte-identical protocol):
```json
{
  "assignment_id": "earworm-frame-lattice-init-repair-v1",
  "base": "b09080567f46adedd1b1f3901a1afab100d3dc2b",
  "authoritative_assignment": "assignment.json",
  "candidate_grid": "Exactly f32/f48/f64: completed32/48/64ms windows,8ms hop. No event gating/cropping/aggregation in lattice path. Frozen event fronts run separately as comparators.",
  "features": "Frozen NSDF full candidate evidence, spectral peak/shape8 normalized power bands, RMS, pitch candidate probability=clamped selected periodicity (unknown remainder), window indices/hash and actual computation/availability. No expected-pitch snapping.",
  "selection": "Validity and group mean matched-query coverage>=.50; maximize intact correct-source retrieval; minimize intact reference Brier; shortest window. If no feasible configuration, stop before calibration/evaluation with failed feasibility evidence.",
  "calibration": "No fitted parameter. uncertainty scalar fixed1 with singleton range[1]; integrity checks only. No representation or retrieval selection.",
  "retrieval": "Fixed recent24-frame suffix ending at last frame RMS>=.01. It is a query-selection rule, no discrete event inference. Search earlier lengths19/24/29 using linear monotone nearest-index mapping within5-frame endpoint-length band. Source continuation at+4,+5,+6,+7 frames must precede query. Valid paired pitch coverage>=.75; cost=mean abs pitch residual+2*(1-coverage)+.05*mean spectral total variation+.02*mean absolute log RMS ratio. Absolute path shift0; relative path one median pitch offset. Accept cost<=.6; two lowest-cost nonoverlapping source windows, deterministic cost/start/end ordering. Weights exp(-cost/.1). Prediction is median continuation pitch+offset; Gaussian interval sigma.08 with.001 floor. Single-window comparator same rule with length1. Unknown1 if no match. No training.",
  "state_budget": "256 frames per active config, at most768 candidate alignments per readout,24 correspondence indices each, two retained matches; track actual serialized candidate scratch and listener data. Shared raw buffer and comparator states counted, zero eviction. Heap/RSS not inferred from serialization.",
  "baselines": "Lattice marginal/present, recency, transition1/2/3 from frozen simple frame-history forecast; absolute sequence, relative sequence, fixed single-window matching. Preserve trim16, PR13 MAP and uncertainty mixture, whole-span and fixed64ms fronts, plus evaluator-only boundary oracle. Strongest comparator=max joint accuracy over all non-oracle models excluding selected lattice/reference; deterministic model-name tie break.",
  "fresh_groups": "40 fresh normalized identities excluding269 prior and all prior seeds,8/8/24; seeds202609217000+i.",
  "controls": "Same four cells; joint intact/reset/removal/swap/whole-figure shuffle/ambiguity plus similar-unrelated current shape control. Current probe byte-identical within pairs, source inventories balanced. Unrelated probe [base,base+2sign,base-7sign], source histories unchanged, target interval\u00b1d around probe end; no matching prior-source region.",
  "recognition_labels": "Evaluator only: acceptable source is earlier Q-prefix occurrence, matched interval overlap>=.80 and end within64ms; reset/unrelated have no source region. Source retrieval gates on intact figures, rejection on unrelated. Memory removal keeps prefix recognition possible but removes continuation evidence. Ambiguous permits either earlier Q occurrence.",
  "transformation_labels": "Changed conditions duration/joint: jointly correct source, uniform pitch offset within.35 semitone and query/source duration ratio within.20. Actual uniform pitch offset is0 in this controlled task. This does not test nonzero transposition generalization. Spectral/energy and alignment residuals reported separately, no timbre category claim.",
  "probability_coordinates": "Frozen relative bins-24..24+unknown, scored in absolute semitone bins-48..72+unknown; source/transformation separate from forecast. Targets are next independently rendered note, disjoint from arrived prefix. Missing/unknown predictions fail known-note accuracy; infinity loss explicit, no clipping.",
  "metrics": "Every forecast front/model/cell/control accuracy,paired success,logloss,Brier,entropy,unknown mass,confidence and fixed10-bin reliability. Separate source/rejection/transformation/coverage/end-error for lattice sequence readouts; comparator source labels not invented. Equal groups.",
  "bootstrap": {
    "seed": 2026092160,
    "resamples": 5000,
    "unit": "paired equal groups",
    "ordinary": [
      0.025,
      0.975
    ],
    "four_cell_familywise": [
      0.00625,
      0.99375
    ],
    "quantile": "inverted_cdf"
  },
  "gates": "Full assignment gates explicit analyze.py: source>=.90overall/.80each,unrelatedfalse<=.10,transform>=.80changed,paired>=.80each,NI lower>=-.10each,joint lower>0overpresent and strongest,proper increases<=.10/.02,allcontrols,familyloss<=.10. No event-F1 gate for lattice.",
  "latency": "Completed-frame audio-availability delay<=160ms AND forecast dispatch-to-commit walltime<=160ms. Context is all arrived chunks at forecast request; report frame computation and dispatch separately. No backdating.",
  "branch_precedence": "Invalid first; C if oracle,source,transformation,non-ambiguity causal controls,safety,positive advantage or latency fails. A if allremaining gates pass. B only prerequisites pass but proper/ambiguity/pair/noninferiority fail. No forced choice or nonsignificance-as-equivalence.",
  "integrity": "Arrived-only worker API, audit guard, prereveal fsync hash chain, future invariance, save/restore trusted serialized listener state reproduces exact forecast bytes (one probe/group), independently reconstructed saved alignments/forecast/scoring, immutable historical hashes exact; numerical tolerance1e-12.",
  "resources": {
    "development_streams": 192,
    "calibration_streams": 192,
    "heldout_streams": 576,
    "scientific_total": 960,
    "prior_entered_failed_streams": 1,
    "fixed_smoke_streams": 1,
    "conservative_all_stream_count": 962,
    "cap": 1000,
    "save_restore": "One already-counted future-invariance probe per group; no extra scientific stream.",
    "prior_compute_charge_seconds": 840.093,
    "additional_seconds_limit": 6300,
    "combined_artifact_bytes": 2147483648,
    "chunks": 32,
    "unit_seconds": 2
  },
  "stop": "One guarded preflight already passed, finite development/calibration,one frozenheldout,one complete successor then awaitreview. Any further invalid execution stops without secondrepair/retry. Scientificbranchrules unchanged.",
  "runtime_repair": "Only worker initialization-order change: np.median on fixed odd/even arrays before byte-identical audit guard. One disposable smoke passed; no scientific audio used."
}
```

Branch precedence remains Invalid first, then C for failed prerequisites (oracle/source/transformation/causal controls/family safety/forecast advantage/latency), A only if every gate passes, otherwise B for readout/proper-score/ambiguity/paired/noninferiority failures after prerequisites pass. No acceptance from construction rules. Controlled short-buffer zero-eviction synthetic study only; not natural music/polyphony/nonzero transposition/long-term retention/appreciation.

One complete successor publication and ordinary PROJECT_STATE.md update will follow, then awaiting-review and stop.
