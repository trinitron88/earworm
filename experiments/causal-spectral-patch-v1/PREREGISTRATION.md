Preregistration: earworm-causal-spectral-patch-v1

Authorized assignment: comment5755164534, version2026-09-21T03:55:02Z.
Exact base:7de087d4dc60ce09ec6d59e50457d44a3d6735da.
Frozen heldout execution commit:d7586c0ca6667806bd99c859f83a1feee722649c.
Package:experiments/causal-spectral-patch-v1/.

No scientific code/rule changed after development freeze5cc14365a2bb73212eb6ef221eac50b523128db3. Both candidates shared each development arrival,with both channel/readout computations counted. Multi-scale selected (source55/64 versus53/64 single); selection was fixed before calibration at1214631a222ea84d0d97f9093eefb4ab108cff86. Calibration fits only the frozen finite mixture-temperature grid;selected.015 by the preregistered Brier tie-break because all three log losses are infinite. Unknown-only outputs remain explicit and unmodified.

Complete saved development/calibration checks pass:8,224/8,228 chained records respectively;16,000 baseline forecasts plus3,360 patch forecasts reconstructed;45,760 spectral channel-frames reconstructed;64 future-invariance probes,16 exact restores and16 captured-silence/missing transactions. Source/seed exclusions and prior non-silent waveform hashes checked. All874 historical files unchanged. No heldout directory/STARTED/audio/exposure. No rerun,extra candidate,threshold change or model repair.

Development and calibration consumed384 counted streams; remaining heldout576 ->960 total. One save/restore and transactional silence/missing probe shares an existing counted future probe per group; both candidate readouts are reported,not hidden as separate data. Conservative elapsed local-work charge at receipt preparation:1302.799s of7200; current new artifact bytes:362208036 of2147483648. No spending. Heldout24 reserved groups sp-16..sp-39 and seeds202609219116..139,all family variants together; no replacements.

Selection and calibration:
```json
{
  "selection": {
    "candidates": [
      {
        "id": "single",
        "source": 0.828125,
        "brier": 0.31607437610905104,
        "mean_serialized_channels_bytes": 429107.75,
        "mean_readout_ns": 7772782.53125
      },
      {
        "id": "multi",
        "source": 0.859375,
        "brier": 0.2283466452479284,
        "mean_serialized_channels_bytes": 885069.125,
        "mean_readout_ns": 11112062.53125
      }
    ],
    "selected": {
      "id": "multi",
      "source": 0.859375,
      "brier": 0.2283466452479284,
      "mean_serialized_channels_bytes": 885069.125,
      "mean_readout_ns": 11112062.53125
    },
    "rule": "validity; max correct source across balanced cells; min forecast Brier; least measured state then compute"
  },
  "calibration": {
    "grid": [
      {
        "temperature": 0.015,
        "log_loss": "+Infinity",
        "brier": 0.27040326106388746
      },
      {
        "temperature": 0.025,
        "log_loss": "+Infinity",
        "brier": 0.2756825470743659
      },
      {
        "temperature": 0.05,
        "log_loss": "+Infinity",
        "brier": 0.28210846523328653
      }
    ],
    "selected": {
      "temperature": 0.015,
      "log_loss": "+Infinity",
      "brier": 0.27040326106388746
    },
    "rule": "min mean intact logloss; Brier tie break; closest initial temperature then lower"
  }
}
```

Frozen source/protocol/config/filterbank/split hashes:
```json
{
  "files": {
    "trim_front.py": "a9a054457b6277ce6badfffe709382302181ea21744198e61bf47b4993fc5e8f",
    "worker.py": "1d186e4ed2e7069fca6755e35c721b8ab573f8ec33777c204f61bd578ccbe2c9",
    "accepted_adapter.py": "fd7e8f88f29e2fa4bb71c14e6ca02c3f209595118f47971ba255ef06cf778747",
    "run.py": "5d69e847585a2e895bf2b43809a4eace12552e3ce0cd38149df85ba3a5551e4e",
    "historical_front.py": "433c0b89b184bb5d74da1bd307d45616f54e6da1d5dff8851e076bbfbc9ac483",
    "patch_labels.py": "2be2da25073d9a3c80cbbdb72a7144081ce04a217faf25fd3adf1ec0341a4877",
    "reference_model.py": "930d3ecc758704ad27941f1fe6b29041d7350814d27198437deedc422f1ddd70",
    "events.py": "0c15fd73847c5133d7b5a86b9c9ee005cc34a69592cdb57d35bda5b2cc363489",
    "scoring.py": "dc694c0cd3fe3bab74fb9fddb7fb6d1518ccf5ef09c01f0494b1672c2f63dbd8",
    "records.py": "4ee555c8de43bb2ae96a23522e3bb345038034c5dc6d929973e83ac5da529485",
    "validation_math.py": "a685fdacffe62131ee8d25ba2967372de50e36663f065fee9e166c9dbf6c7e2c",
    "aggregation_front.py": "3a78d91624637f7ab7dd814f2455d9746b49dbc21b76c0aa4e16701c86ff7805",
    "baseline_validation.py": "66e53f66a8cedcde732d3da0b0d93367feb63fd27098f9dafd8dfd1e1bb42da2",
    "model.py": "b0ed31269dfeffa31e17a66093f9c2886f39d5135b5f5a5a2f08c887d98337e0",
    "lattice_validation.py": "1a86bf4ab682f4269226c3f51fe19cb090e542ceac4b4fbed44efe9ff1b7b101",
    "stimuli.py": "03e117a76778d6258fe3eeec3557495cbaf11addc0de5fb15699c6b4b52c8b41",
    "frozen_lattice.py": "4f90ffa69dbaa4055920f68048153f362fc11ab03709cfdbe398a5bbe9738a7e",
    "calibrate.py": "94f99e0ed9d83fd6a666b9413113748ddd22ace55cbef115bf29f25f04e20a29",
    "select.py": "bdd6e802e2aa157384a49cc27eec875c05b65c13755ae9928ad8f8a5f237bfda",
    "verify.py": "dffbfcaa2beeada8e9a38a9004896f7d0e4670eaf729beef84f16530dbbcd178",
    "analyze.py": "a3c3a6b13fb963331fbbbf276f7336fa09d1bcde372e853922f0735bc3304322",
    "validation/independent_scores.py": "a79b39588b29ad49f5f27186ec6b261bfbc791cd0a718f6e2ff367fc1da8a8db",
    "validation/accounting.py": "2d23c1633e9c6297f7d8744ad09d61a4fdf71d9d26d0591b23411bcaa2b4645c",
    "validation/patch_arithmetic.py": "162ef5b04861a415ce216529565ad5db0e8e1cac43c2a2cb575bef2ddf2cfdf2",
    "protocol.json": "9f130af29499059ac1d7480849253b3d1670eeef8580b99553073df5645883d5",
    "initial_model.json": "29c8e66431005cc011f5c366013fc94f1682908604cfe9ec5ce5fac442e5a02c",
    "calibration_model.json": "c084e5c821933c46d9c8f2d7ddba7d6b2c8005544fc475453b36c26607227014",
    "frozen_model.json": "b4f3851f4509a4bb273adf2e9d2213e2527b28bfca30c0439f281b00bd8737b6",
    "development_selection.json": "0e835b2296c2314242039f4aa584be5578fa4a13233172d7e28716184334d6c6",
    "calibration_fit.json": "e38697852bea43a575854939e0e6423368abdb10d98c1266cffc54863f1dd538",
    "filterbank.json": "294bc441b3d9986a7ace710a8878d3a526f4d7eeb2891370dedb51dc888f4109",
    "split_manifest.json": "2056f72c021ffc14b2100b9b13380cf4896227bb4c4660ea9731bab793ce0bf7",
    "excluded_prior_motifs.json": "2de08786377fdd2defcd797bbe71ec9671bb1720b6b237b951c3f9b79e510fb5",
    "prior_wave_hashes.json": "f59251bd436f3c07a05669028333f46a564edfacf37af19bf4d338100434e1b6",
    "prior_artifact_hashes.json": "11eb8f522118c23b74d2cefc47fb36b0afd84737e8ea0c1bd72b76b7aae2863e",
    "development_freeze.json": "7b81264b850244f0fe7d46e99ef37f0d25e901404c75cc2638433aa81a17c2bc",
    "assignment.json": "629bf035855aefc3661d28650fc777c5476091cdda42f5b86cdfaa4588a76d7c"
  },
  "execution_code_sha256": "08ad0f8ab94efc6f6e85e9f8a272535c9b865d2fb0dbcb122ec0a800fd0aab76",
  "frozen_at": "2026-09-21T04:37:40.040763+00:00",
  "development_and_calibration_valid": true,
  "heldout_unstarted": true,
  "no_scientific_source_change_after_development": true
}
```

Complete frozen representation,transform ranges,query/continuation/state budgets,coordinates,clocks,controls,bootstrap,gates and branch precedence:
```json
{
  "assignment": "earworm-causal-spectral-patch-v1",
  "base": "7de087d4dc60ce09ec6d59e50457d44a3d6735da",
  "development_candidates": [
    "single:64ms completed Hann",
    "multi:64ms+128ms completed Hann"
  ],
  "features": "16kHz PCM,16ms hop, first shared output128ms after reset.4096-point FFT.135 log bands,edges80*2^(i/24),i0..135 (80..3948.059713Hz).Fractional overlap of each linear FFT bin cell with each log band,rows normalized to sum1; exact weights in filterbank.json. Retain band powers,unwindowed RMS,PCM bounds/hash and actual computation/availability. identity=unit-L2 log1p(1000*bandpower/max(total,1e-20)); silence RMS<.01. The matcher does not consume pitch estimates.",
  "readout": "Fixed frozen NSDF adapter on completed64ms windows supplies only the continuation pitch/probability coordinate, not matching or segmentation. Candidate identity uses spectral channels; absolute and invariant readouts are separate. Preserve original unshifted band powers and energy; shifted spectral residual,timing ratio and energy log residual remain separate interpretations.",
  "alignment": "Fixed last16-frame suffix ending at latest RMS>=.01 frame; source lengths12/16/20. Monotone nearest-integer linear correspondence (at most4-frame length deviation). Earlier continuation frames+2,+3,+4 must precede query. Uniform shifts integer semitones-6..6 (2bins/semitone); absolute comparator only0. Mean cosine distance across aligned frames/channels with cropped overlap renormalized; zero-support similarity0. Accept cost<=.25; lexicographic cost/start/end/abs-shift/shift. Keep at most2 nonoverlapping source intervals. No event inference, expected-pitch snapping, supplied boundaries or learned controller.",
  "forecast": "Earlier continuation median observed pitch plus estimated shift; Gaussian relative bins-24..24 sigma.08,unknown bin,uniform floor.001. Two matches weighted exp(-cost/temperature). No match or unavailable anchor gives unknown1. Query hash is fsynced before retrieval; forecast fsynced before target PCM generation/extraction. Future target is a separate next-note waveform, no overlap with arrived prefix.",
  "selection": "Both fixed candidates share each development PCM arrival once; report both candidate readout computations and channels. One selection after complete development validity: maximum source recognition across balanced four cells,minimum intact Brier,minimum serialized channel bytes,minimum measured readout time. No other candidate or selection.",
  "calibration": "One scalar match-mixture temperature in [0.015,0.025,0.05],initial.025. Saved calibration matching evidence only; minimum mean intact logloss,then Brier,then closest.025,then lower. No representation/alignment/threshold changes. Save calibration outcomes at execution temperature unchanged; fitted config used only heldout.",
  "groups": "40 fresh normalized identities and seeds;8 development/8 calibration/24 heldout; all family variants one split. Exclude all309 prior identities and prior seeds. Independently rendered non-silent units and complete prefixes must not equal prior saved hashes; shared zero silence and required within-study paired/repeated bytes are explicit exceptions.",
  "cells": "Unchanged; nonzero transposition only (balanced -5,-3,+3,+5); stretch only (.8,1.25 balanced); timbre only. No combinations. Each group20 episodes:8 intact (fourcells*two bindings),12 additional controls in unchanged cell. Four future-invariance probes/group; one also carries save/restore and transactional captured-silence/missing probes. No extra input stream is replayed.",
  "controls": "Equal paired current bytes,source inventory,duration,energy,timbre/pitch set and source order/recency counterbalance. Reset and continuation-removal require accuracy<=.55,paired<=.10,paired-distribution TV<=1e-9. Swap exact opposite-binding distribution within1e-9 and paired success>=.80. Shuffle accuracy drop<=.10. Ambiguous two outcomes require combined mass>=.90,each within.10 of.50,max bin<=.60. Unrelated false matches<=.10. Silence/missing probe: save current state,arrive captured-zero1024 samples,verify captured-silence status,restore; missing1024 samples must have null PCM reference,generate no feature and invalidate all forecasts to unknown; restore original forecast bytes. Missing advances the sample clock and flushes transient buffers; it remains an explicit unavailable discontinuity until reset. No zero PCM is invented. This is a transactional probe on an already-counted stream, not a new scientific replay.",
  "labels": "Evaluator-only source region: predicted source interval overlap fraction>=.80,end within64ms. Transformations scored independently of source correctness: pitch shift within.5 semitone in transpose cell; duration ratio within.10 in stretch; timbre-change Boolean residual>=.08 in timbre cell. Report all three labels in all cells,including false positives. These construction labels are not human perceptual identity.",
  "comparators": "Equal raw arrivals/access: patch present,marginal,recency,transition1/2/3,absolute,invariant; frozen PR16 f32 absolute/reference/single and its frame present/recency/transitions; frozen trim16,PR13 MAP/mixture,whole-span and fixed64ms paths; evaluator-only supplied-boundary oracle. Strongest fair operational model is maximum mean four-cell intact accuracy excluding primary and oracle,model-name tie break. Non-adopted high-scoring comparators remain non-adopted.",
  "bootstrap": {
    "seed": 202609219150,
    "resamples": 5000,
    "unit": "paired equal groups",
    "ordinary_quantiles": [
      0.025,
      0.975
    ],
    "eight_cell_comparator_familywise_quantiles": [
      0.003125,
      0.996875
    ],
    "method": "inverted_cdf"
  },
  "gates": "Validity first. Source>=.90 overall/.80each,unrelatedfalse<=.10. Separate transform accuracy>=.80each changed cell. Paired forecast>=.80each. Positive lower95 advantage over patch present across four cells and removal in unchanged cell. Operational-minus-oracle and minus strongest lower familywise95>=-.10each cell. Aggregate-four-cell logloss increase<=.10,Brier<=.02 versusoracle; per-cell results retained. Frozen controls,all-family loss<=.10,feature and durable forecast latency<=.160s,independent raw/identity/realization reconstruction.",
  "branch_precedence": "Invalid first. C if oracle,identity/rejection,history dependence,paired success,noninferiority,non-ambiguity causal controls,silence/missing,preservation,latency or family safety fails. A only every remaining gatepasses. B only prerequisites pass but transformation and/or proper-score/ambiguity uncertainty fails. C ends handcrafted synthetic continuous-front sequence; no automatic fourth front.",
  "clocks": "Audio availability=(available_sample-frame_end)/16000; actual frame computation separately compared to chunk dispatch/return. Durable forecast delay is first forecast dispatch to fsynced forecast commit. No backdating. 128ms context windows are completed, not lookahead.",
  "state": "<=128 patch frames,2 channels of135 bins,original raw<=32chunks,shared frozen comparator buffers/events/lattice frames counted; one/two matches;<=5000 tested candidate alignments/readout. Record vectorized scratch arrays,config/filterbank,retained forecasts,status/counters and raw state; report serialized/pickled state separately from process RSS. No eviction; evaluator archives not predictor memory.",
  "tolerance": "Independent band powers atol1e-9/rtol1e-12; normalized identity,RMS,forecast and alignment arithmetic1e-12; original comparator checks unchanged; byte hashes exact.",
  "resources": {
    "streams": 960,
    "hard_total_stream_cap": 1000,
    "compute_seconds": 7200,
    "new_artifact_bytes": 2147483648,
    "chunks": 32,
    "completed_waveform_seconds": 2,
    "development_candidate_stream_passes": 192,
    "development_candidate_readout_evaluations": "both candidates within each of160 main episodes; no duplicate PCM arrival",
    "additional_silence_missing_transactions": 40
  },
  "stop": "One development selection,one calibration,one heldout. Any execution/integrity mismatch stops with immutable evidence; no repair/retry,group replacement,retuning,spending,downloads,training or MERT change. Publish complete successor,await review,stop.",
  "limitations": "Synthetic monophonic short buffer;zero eviction. No natural performance,polyphony,Bach familiarity,long-term retention,perceptual identity or appreciation claim. Human judgments separate. Predeclared grids are not general transformation invariance."
}
```

The semantic distinctions remain binding:source occurrence,each transformation,forecast and realization residuals are separately reported. No superiority requirement over near-ceiling comparators; require history dependence and the stated familywise noninferiority. No combined transformations. B permits only transformation/uncertainty failure after all identity/history/causality/preservation/latency/safety/forecast prerequisites pass. C ends this handcrafted synthetic front sequence; no automatic fourth front. Invalid stops without repair/replay. No natural-performance,polyphony,perceptual-identity,nonzero-eviction,long-term-retention or appreciation claim.

One heldout execution,one complete successor with PROJECT_STATE.md,then awaiting-review and stop.
