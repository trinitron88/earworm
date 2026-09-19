"""Frozen Experiment08 protocol, extraction, development, evaluation, and replay.

Routing into the extractor is id/path only. Metadata is used outside inference
for split selection, history construction, supervision on fit groups, and scoring.
No test labels or edit labels enter accounts_reader. Earlier files are read-only.
"""
from __future__ import annotations
import os,sys,json,time,hashlib,argparse
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'accounts_results';FEATURES=ROOT/'accounts_features'
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import numpy as np
from scipy.io import wavfile
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from remember_changes_acoustics import describe_audio
from confidence_reader import candidate_evidence,compatible
from accounts_reader import PARAMETERS,FEATURE_NAMES,evidence,score,simple_scores,explain,decide,description_digest

def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def plain(x):
    if isinstance(x,dict):return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [plain(v) for v in x]
    if isinstance(x,np.ndarray):return plain(x.tolist())
    if isinstance(x,np.generic):return plain(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def write(path,x):Path(path).write_text(json.dumps(plain(x),indent=2,allow_nan=False)+'\n')
def load(path):return json.loads(Path(path).read_text())
def sources():return {p.name:sha(p) for p in [ROOT/x for x in ('accounts_stimuli.py','accounts_reader.py','accounts_experiment.py','remember_changes_acoustics.py','confidence_reader.py','incomplete_matcher.py')]}
def freeze():
    OUT.mkdir(exist_ok=True);p=OUT/'protocol.json'
    if p.exists():
        assert load(p)['source_sha256']==sources(),'Implementation changed after protocol freeze; disclose amendment rather than overwriting.';return
    write(p,dict(experiment=8,frozen_utc=utc(),source_sha256=sources(),
        question='Recover memory and acoustic edits without a supplied edit family or fixed coverage fraction; retain competing explanations and observation uncertainty.',
        split={'fit':'e00-e03: one group per length; core families only','calibration':'e04-e07: one per length; core only','held_out':'e08-e23: four groups per length; no tuning'},
        data={'groups':24,'lengths':[4,6,8,10],'prior_patterns_excluded':1032,'fresh_base_patterns':264,'blocks':1128,'query_seconds':2},
        inputs='PCM and sample rate; acoustic descriptions only in matching. No generator note counts, pitches, edit labels, source, or split as predictor features. Opaque handles route outputs.',
        controls=['Overlapping length/count/gap/edit mixtures and count/envelope baselines','Weak, masked, and merged observations versus actual omissions','Exactly ambiguous source waveforms and nonexclusive observation explanations'],
        alignment=PARAMETERS,feature_names=FEATURE_NAMES,
        fit='StandardScaler plus L2 LogisticRegression C=1, balanced classes, random_state=8, max_iter=2000; pairwise source labels from fit core groups only. Logits are support scores, not probabilities.',
        calibration='Across source A/B crossed histories (one head plus eight identical distractors): choose score threshold maximizing correct singleton retrieval under <=5% empirical absent-history false acceptance; ties favor fewer false accepts then stricter threshold. Apply one threshold to all families and lengths. Return every memory at/above threshold.',
        frozen_baseline='Unchanged Experiment07 evidence_sets with its existing residual threshold and five-sixths/full-query coverage gates.',
        simple_baselines='Raw detected-event count difference; L2 distance of unit-normalized 64-bin RMS envelopes. Each threshold independently calibrated by the same criterion.',
        stages=['core','delete_transpose','delete_timing','delete_detune'],
        scoring={'source':'Origin membership and correct-singleton fraction separate; ordinary absent-history acceptance; ambiguity cases require both compatible memories and no extra.',
            'best_alignment':'Evaluate top alignment of the actually uniquely retrieved true source; exact missing reference set and inserted-event count; all absolute per-event pitch changes within .20 semitone and onset changes within .015 s; require full true surviving correspondence. Generator truth is evaluator-only.',
            'account_set':'Same strict joint criterion but any retained alignment; reported separately from best.',
            'observation_controls':'Report detection count, nonfinite/quality-filtered events, missing positions, quiet-gap assertions, unresolved gaps, and false quiet assertions for physically present weak/masked/merged notes. Do not score hidden mask cause as recoverable.',
            'uncertainty':'All missing correspondences retain physical_cause=not_identified. Quiet-at-predicted-location is acoustic support under this fit, not proof of a performer action or human identity.'},
        delay_controls={'delays_s':[0,16],'modes':['intact','drop_reference','reset_before_query'],'intervening_sound':'eight completed 2s distractor blocks','capacity':'12 acoustic entries; no decay or interference learning'},
        availability='Only completed supplied 2s blocks; batch cache timings explicitly distinct from fresh sequential waveform replay. Logical online schedule is block end plus computation, serialize backlog; wall times and output-ready timestamps recorded after matching AND explanation. No live continuous-stream claim.',
        replay='Four held-out groups (one per length), A source, six predetermined families (exact,delete_rest,mask_present,delete_transpose,delete_timing,delete_detune), 16s intact/drop/reset; each block described afresh. Four paired history swaps and four future-prefix pairs. No similarity cache in replay.',
        limitations=['Synthetic monophonic additive phrases; known completed windows; hand-supplied edit vocabulary; limited alignment beam; four fit and four calibration groups; generalization measured on sixteen groups, not independent trials.','A full acoustic memory store is supplied; this is not learned recurrent memory or subjective hearing.','MERT checkpoint remains frozen and unused in new scoring; no new MERT inference, fitting, or foundation-model training.','No human perceptual identity inference; human pilot remains separate.'],paid_external_compute_usd=0))

def read_audio(path):
    sr,a=wavfile.read(path);assert sr==24000 and a.shape==(48000,) and a.dtype==np.float32 and np.isfinite(a).all();return a,sr
def describe_blocks(block_ids,routing):
    FEATURES.mkdir(exist_ok=True);timings=load(FEATURES/'timings.json') if (FEATURES/'timings.json').exists() else {}
    start=time.perf_counter()
    for i,bid in enumerate(block_ids):
        path=FEATURES/f'{bid}.npz'
        if path.exists():continue
        pcm,sr=read_audio(routing[bid]);wall_start=utc();t=time.perf_counter();d=describe_audio(pcm,sr);elapsed=time.perf_counter()-t
        np.savez_compressed(path,**{k:np.asarray(v) for k,v in d.items()})
        timings[bid]=dict(wall_start_utc=wall_start,wall_ready_utc=utc(),compute_s=elapsed,pcm_sha256=hashlib.sha256(pcm.tobytes()).hexdigest(),description_digest=description_digest(d),fresh=True,model_input_fields=['pcm','sample_rate'])
        if i%60==0:print(f'Extract {i+1}/{len(block_ids)} ({time.perf_counter()-start:.1f}s)',flush=True);write(FEATURES/'timings.json',timings)
    write(FEATURES/'timings.json',timings)
def descriptions(ids):
    out={}
    for bid in ids:
        with np.load(FEATURES/f'{bid}.npz',allow_pickle=False) as z:out[bid]={k:z[k] for k in z.files}
    return out
def group_refs(g):return [g['reference_a_id'],g['reference_b_id']]+g['distractor_ids']+[g['twin_id']]
def pair_table(groups,blocks,D,baseline=True):
    result={};old=load(ROOT/'confidence_results/frozen_config.json')['configs']['evidence_sets'];start=time.perf_counter()
    for g in groups:
        queries=[b for b in blocks if b['group_id']==g['id'] and b['role']=='query']
        for q in queries:
            result[q['id']]={}
            for rid in group_refs(g):
                ev=evidence(D[rid],D[q['id']]);simple=simple_scores(D[rid],D[q['id']]);oldpass=compatible(candidate_evidence(D[rid],D[q['id']]),old) if baseline else False
                result[q['id']][rid]=dict(evidence=ev,**simple,old07=bool(oldpass))
        print(f'Align {g["id"]}: {len(queries)} queries ({time.perf_counter()-start:.1f}s)',flush=True)
    return result
def histories(g,q,mode='intact',delay=16):
    other=g['reference_b_id'] if q['source']=='a' else g['reference_a_id'];tail=g['distractor_ids'] if delay else []
    present=[q['reference_id']]+tail;absent=[other]+tail
    if mode=='drop_reference':present=tail.copy();absent=tail.copy()
    if mode=='reset_before_query':present=[];absent=[]
    return present,absent
def value(row,method,config):return score(row['evidence'],config) if method=='accounts' else row[method]
def accepted(table,ids,method,config):
    if method=='old07':return [i for i in ids if table[i]['old07']]
    threshold=config['threshold'] if method=='accounts' else config['baseline_thresholds'][method]
    return [i for i in ids if value(table[i],method,config)>=threshold]
def threshold_fit(groups,queries,table,method,config):
    G={g['id']:g for g in groups};trials=[];vals=[]
    for q in queries:
        pos,neg=histories(G[q['group_id']],q);scores={k:value(v,method,config) for k,v in table[q['id']].items()}
        trials.append((q['reference_id'],pos,neg,scores));vals.extend(scores[i] for i in set(pos+neg))
    levels=np.unique(vals);levels=np.r_[levels,np.nextafter(levels[-1],np.inf)];best=None
    for threshold in levels:
        correct=false=0
        for true,pos,neg,s in trials:
            correct+=([i for i in pos if s[i]>=threshold]==[true]);false+=any(s[i]>=threshold for i in neg)
        if false/len(trials)>.05+1e-12:continue
        candidate=(correct,-false,float(threshold))
        if best is None or candidate>best:best=candidate
    return dict(threshold=best[2],correct_singletons=best[0],false_acceptances=-best[1],positive_n=len(trials),negative_n=len(trials))

def develop(manifest,routing):
    groups=[g for g in manifest['groups'] if g['split']!='held_out'];ids=[b['id'] for b in manifest['blocks'] if b['split']!='held_out' and b['phase']=='core']
    describe_blocks(ids,routing);D=descriptions(ids);blocks=[b for b in manifest['blocks'] if b['id'] in D];table=pair_table(groups,blocks,D)
    X=[];Y=[]
    for q in blocks:
        if q['role']!='query' or q['split']!='fit':continue
        g=next(g for g in groups if g['id']==q['group_id'])
        for rid in group_refs(g)[:-1]:X.append(table[q['id']][rid]['evidence']['features']);Y.append(int(rid==q['reference_id']))
    scaler=StandardScaler().fit(X);model=LogisticRegression(C=1.,class_weight='balanced',random_state=8,max_iter=2000).fit(scaler.transform(X),Y)
    config=dict(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),feature_names=FEATURE_NAMES,fit_pairs=len(Y),fit_positive_pairs=sum(Y))
    calq=[b for b in blocks if b['role']=='query' and b['split']=='calibration'];calg=[g for g in groups if g['split']=='calibration'];settings={}
    for method in ('accounts','count','envelope'):settings[method]=threshold_fit(calg,calq,table,method,config)
    config.update(threshold=settings['accounts']['threshold'],baseline_thresholds={k:settings[k]['threshold'] for k in ('count','envelope')},calibration=settings,frozen_utc=utc(),source_sha256=sources(),protocol_sha256=sha(OUT/'protocol.json'))
    write(OUT/'frozen_config.json',config);write(OUT/'development_pairs.json',table)
    print('Frozen calibration: '+json.dumps(settings),flush=True)

def strict_account(p,ref,q,rd,qd):
    """Evaluator only: require every surviving reference and insertion accounted for."""
    actual=[e for e in q['notes'] if e['present']];surviving={e['ref_position']:e for e in actual if e['ref_position'] is not None}
    missing=set(range(len(ref['notes'])))-set(surviving);inserted=sum(e['ref_position'] is None for e in actual)
    if set(p['missing_reference'])!=missing or len(p['inserted_query'])!=inserted:return False
    if {a for a,b in p['matched_pairs']}!=set(surviving):return False
    # Event indices must correspond to the waveform event at that reference's edited onset.
    for k,(ri,qi) in enumerate(p['matched_pairs']):
        if ri not in surviving:return False
        expected=surviving[ri];onset=float(qd['event_onset_s'][qi]);nearest=min(actual,key=lambda e:abs(e['onset']-onset))
        if nearest['ref_position']!=ri:return False
        if abs(p['absolute_pitch_change_semitones'][k]-(expected['pitch']-ref['notes'][ri]['pitch']))>.20:return False
        if abs(p['onset_change_s'][k]-(expected['onset']-ref['notes'][ri]['onset']))>.015:return False
    return True

def evaluate(manifest,routing):
    config=load(OUT/'frozen_config.json');assert config['source_sha256']==sources();groups=[g for g in manifest['groups'] if g['split']=='held_out'];allrows=[];allpairs={};ambiguity=[];query_details=[];D={};byid={b['id']:b for b in manifest['blocks']}
    for stage in ('core',)+tuple(manifest['stack_order']):
        ids=[b['id'] for b in manifest['blocks'] if b['split']=='held_out' and (b['phase']=='core' if stage=='core' else b['family']==stage)]
        describe_blocks(ids,routing);D.update(descriptions(ids));stage_blocks=[byid[i] for i in ids];pairs=pair_table(groups,stage_blocks,D);allpairs.update(pairs)
        for g in groups:
            for q in [b for b in stage_blocks if b['role']=='query' and b['group_id']==g['id']]:
                tab=pairs[q['id']];ref=byid[q['reference_id']];e=tab[q['reference_id']]['evidence'];accounts=explain(D[q['reference_id']],D[q['id']],e)
                for delay in (0,16):
                    for mode in ('intact','drop_reference','reset_before_query'):
                        pos,neg=histories(g,q,mode,delay)
                        for method in ('accounts','old07','count','envelope'):
                            a=accepted(tab,pos,method,config);b=accepted(tab,neg,method,config);correct=a==[q['reference_id']]
                            jointbest=correct and bool(accounts) and strict_account(accounts[0],ref,q,D[q['reference_id']],D[q['id']]) if method=='accounts' else None
                            jointset=correct and any(strict_account(p,ref,q,D[q['reference_id']],D[q['id']]) for p in accounts) if method=='accounts' else None
                            allrows.append(dict(query_id=q['id'],group_id=g['id'],length=g['length'],stage=stage,family=q['family'],source=q['source'],delay_s=delay,mode=mode,method=method,accepted_present=a,accepted_absent=b,correct_singleton=correct,source_covered=q['reference_id'] in a,absent_false_accept=bool(b),joint_best=jointbest,joint_account_set=jointset))
                present,_=histories(g,q);a=accepted(tab,present,'accounts',config);chosen=[]
                for rid in a:chosen.append(dict(memory_id=rid,support_logit=score(tab[rid]['evidence'],config),accounts=explain(D[rid],D[q['id']],tab[rid]['evidence'])))
                query_details.append(dict(query_id=q['id'],family=q['family'],group_id=g['id'],accepted=chosen,observed_raw_events=len(D[q['id']]['event_onset_s']),reliable_events=e['query_events'],truth_present_events=sum(x['present'] for x in q['notes']),true_reference_evidence=e))
            if stage=='core':
                qid=g['ambiguity_query_id'];ids=[g['reference_a_id'],g['twin_id']]+g['distractor_ids'];expected={g['reference_a_id'],g['twin_id']}
                for method in ('accounts','old07','count','envelope'):
                    for order in ('original','reversed'):
                        a=accepted(pairs[qid],ids if order=='original' else list(reversed(ids)),method,config)
                        ambiguity.append(dict(group_id=g['id'],query_id=qid,method=method,order=order,expected=sorted(expected),accepted=a,exact_set=set(a)==expected,both_covered=expected.issubset(a)))
        print(f'Completed frozen stage: {stage}',flush=True)
        write(OUT/'trials.json',allrows);write(OUT/'query_details.json',query_details);write(OUT/'ambiguity.json',ambiguity);write(OUT/'held_out_pairs.json',allpairs)
    summarize(manifest,allrows,ambiguity,query_details)

def summary_rows(rows):
    n=len(rows);return dict(n=n,correct_singletons=sum(r['correct_singleton'] for r in rows),source_covered=sum(r['source_covered'] for r in rows),absent_false_accept=sum(r['absent_false_accept'] for r in rows),joint_best=sum(bool(r['joint_best']) for r in rows),joint_account_set=sum(bool(r['joint_account_set']) for r in rows))
def summarize(manifest,rows,ambiguity,details):
    primary=[r for r in rows if r['mode']=='intact' and r['delay_s']==16];summary=dict(created_utc=utc(),primary_by_method={m:summary_rows([r for r in primary if r['method']==m]) for m in ('accounts','old07','count','envelope')},families={},groups={},lengths={},controls={},ambiguity={},observation={})
    for f in manifest['core_families']+manifest['stack_order']:summary['families'][f]=summary_rows([r for r in primary if r['method']=='accounts' and r['family']==f])
    for g in [g for g in manifest['groups'] if g['split']=='held_out']:summary['groups'][g['id']]=summary_rows([r for r in primary if r['method']=='accounts' and r['group_id']==g['id']])
    for n in (4,6,8,10):summary['lengths'][str(n)]=summary_rows([r for r in primary if r['method']=='accounts' and r['length']==n])
    for d in (0,16):
        for m in ('intact','drop_reference','reset_before_query'):summary['controls'][f'{d}s_{m}']=summary_rows([r for r in rows if r['method']=='accounts' and r['delay_s']==d and r['mode']==m])
    for m in ('accounts','old07','count','envelope'):
        a=[r for r in ambiguity if r['method']==m];summary['ambiguity'][m]=dict(n=len(a),exact_sets=sum(r['exact_set'] for r in a),both_covered=sum(r['both_covered'] for r in a))
    B={b['id']:b for b in manifest['blocks']}
    for f in ('delete_rest','delete_closed','delete_two','weak_present','mask_present','mask_absent','merged','legitimate_rest'):
        items=[d for d in details if d['family']==f];s=dict(n=len(items),fewer_raw_events=0,fewer_reliable_events=0,correct_singleton=0,missing_correspondence_trials=0,unresolved_gap_trials=0,quiet_gap_trials=0,false_quiet_on_present_trials=0,truth_deleted_localized=0,physical_causal_claims=0)
        for d in items:
            q=B[d['query_id']];s['fewer_raw_events']+=d['observed_raw_events']<d['truth_present_events'];s['fewer_reliable_events']+=d['reliable_events']<d['truth_present_events'];good=len(d['accepted'])==1 and d['accepted'][0]['memory_id']==q['reference_id'];s['correct_singleton']+=good
            if not good or not d['accepted'][0]['accounts']:continue
            p=d['accepted'][0]['accounts'][0];gaps=p['missing_evidence'];s['missing_correspondence_trials']+=bool(gaps);s['unresolved_gap_trials']+=any(v['status']=='unresolved_observation' for v in gaps);s['quiet_gap_trials']+=any(v['status']=='quiet_at_predicted_location' for v in gaps)
            present={e['ref_position'] for e in q['notes'] if e['present'] and e['ref_position'] is not None};deleted={e['ref_position'] for e in q['notes'] if not e['present']}
            s['false_quiet_on_present_trials']+=any(v['status']=='quiet_at_predicted_location' and v['reference_event'] in present for v in gaps)
            s['truth_deleted_localized']+=bool(deleted) and set(p['missing_reference'])==deleted
            s['physical_causal_claims']+=sum(v['physical_cause']!='not_identified' for v in gaps)
        summary['observation'][f]=s
    write(OUT/'summary.json',summary);print(json.dumps(summary['primary_by_method'],indent=2),flush=True)

def fresh_trial(sequence,reference_handle,query_path,config,mode='intact',delay=16):
    """Finite memory, actual fresh PCM computations, output after all explanations."""
    memory=[];clock=0.;available=0.;records=[];start=utc()
    for handle,path in sequence:
        pcm,sr=read_audio(path);arrival_start=clock;clock+=2.;wall=utc();t=time.perf_counter();d=describe_audio(pcm,sr);elapsed=time.perf_counter()-t
        available=max(clock,available)+elapsed;memory.append((handle,d));memory=memory[-12:]
        records.append(dict(handle=handle,audio_start_s=arrival_start,audio_complete_s=clock,logical_description_ready_s=available,compute_s=elapsed,wall_compute_start_utc=wall,wall_description_ready_utc=utc(),description_digest=description_digest(d),pcm_sha256=hashlib.sha256(pcm.tobytes()).hexdigest()))
    if mode=='drop_reference':memory=[(h,d) for h,d in memory if h!=reference_handle]
    if mode=='reset_before_query':memory=[]
    state_digest=hashlib.sha256(''.join(h+description_digest(d) for h,d in memory).encode()).hexdigest();before=[description_digest(d) for h,d in memory]
    pcm,sr=read_audio(query_path);arrival_start=clock;clock+=2.;wall=utc();t=time.perf_counter();q=describe_audio(pcm,sr);extract=time.perf_counter()-t;qdigest=description_digest(q)
    desc_ready=max(clock,available)+extract;t=time.perf_counter();decision=decide(memory,q,config);infer=time.perf_counter()-t;wallready=utc();output_ready=desc_ready+infer
    assert [description_digest(d) for h,d in memory]==before and description_digest(q)==qdigest
    return dict(wall_trial_start_utc=start,history=records,mode=mode,delay_s=delay,memory_state_digest=state_digest,query_audio_start_s=arrival_start,query_audio_complete_s=clock,query_description_ready_s=desc_ready,decision_available_s=output_ready,latency_after_query_end_s=output_ready-clock,query_extract_s=extract,match_and_explain_s=infer,wall_query_compute_start_utc=wall,wall_decision_ready_utc=wallready,query_description_digest=qdigest,feature_cache_hit=False,similarity_cache_hit=False,decision=decision)

def replay(manifest,routing):
    config=load(OUT/'frozen_config.json');B={b['id']:b for b in manifest['blocks']};groups=[g for g in manifest['groups'] if g['id'] in ('e08','e09','e10','e11')];runs=[];start=time.perf_counter()
    for g in groups:
        for family in ('exact','delete_rest','mask_present','delete_transpose','delete_timing','delete_detune'):
            q=next(b for b in B.values() if b['group_id']==g['id'] and b['source']=='a' and b['family']==family and b['role']=='query')
            seq=[(i,routing[i]) for i in [g['reference_a_id']]+g['distractor_ids']]
            for mode in ('intact','drop_reference','reset_before_query'):
                r=fresh_trial(seq,g['reference_a_id'],routing[q['id']],config,mode);r.update(query_id=q['id'],family=family,group_id=g['id'],true_reference=q['reference_id']);runs.append(r)
            print(f'Fresh replay {g["id"]}/{family}: {len(runs)} runs ({time.perf_counter()-start:.1f}s)',flush=True);write(OUT/'fresh_replays.json',runs)
    swapped=[];prefix=[]
    for g in groups:
        q=next(b for b in B.values() if b['group_id']==g['id'] and b['source']=='a' and b['family']=='delete_rest' and b['role']=='query')
        seq=[(i,routing[i]) for i in [g['reference_b_id']]+g['distractor_ids']]
        for mode in ('intact','drop_reference','reset_before_query'):
            r=fresh_trial(seq,g['reference_b_id'],routing[q['id']],config,mode);r.update(query_id=q['id'],group_id=g['id']);swapped.append(r)
            paired=next(x for x in runs if x['query_id']==q['id'] and x['mode']==mode)
            if mode!='intact':assert r['memory_state_digest']==paired['memory_state_digest'] and r['decision']==paired['decision']
        # Entire available prefix is recomputed for two different not-yet-arrived tails.
        first,sr=read_audio(routing[q['id']]);ds=[];tails=g['distractor_ids'][:2]
        for tail in tails:
            future,_=read_audio(routing[tail]);arrived=np.concatenate([first,future])[:len(first)]
            ds.append(describe_audio(arrived,sr))
        assert description_digest(ds[0])==description_digest(ds[1])
        mem=[]
        for bid in [g['reference_a_id']]+g['distractor_ids']:
            pcm,sr=read_audio(routing[bid]);mem.append((bid,describe_audio(pcm,sr)))
        decisions=[decide(mem,d,config) for d in ds];assert decisions[0]==decisions[1]
        prefix.append(dict(group_id=g['id'],query_id=q['id'],different_future_audio=True,arrived_prefix_equal=True,description_equal=True,emitted_decision_equal=True))
    write(OUT/'swapped_replays.json',swapped);write(OUT/'prefix_checks.json',prefix)
    timings=load(FEATURES/'timings.json');lat=[r['latency_after_query_end_s'] for r in runs+swapped]
    write(OUT/'replay_summary.json',dict(fresh_trials=len(runs)+len(swapped),fresh_blocks=sum(len(r['history'])+1 for r in runs+swapped),prefix_pairs=len(prefix),prefix_extra_blocks=4*11,output_timestamps_complete=True,latency_median_s=float(np.median(lat)),latency_max_s=max(lat),feature_cache_hit=False,similarity_cache_hit=False,memory_descriptions_unchanged=True,reset_swapped_states_equal=True,
        exact_wall_times_recorded=True,logical_time='Simulated sound arrivals, serialized measured computation; actual wall ready times separately recorded. Audio files processed faster than real time, not a live microphone test.',extract_blocks=len(timings)))

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','develop','evaluate','replay']);args=p.parse_args();freeze()
    manifest=load(ROOT/'accounts_stimuli/manifest.json');rr=load(ROOT/'accounts_stimuli/routing.json');assert all(set(b)=={'id','audio_path'} for b in rr);routing={b['id']:b['audio_path'] for b in rr}
    if args.phase=='develop':develop(manifest,routing)
    elif args.phase=='evaluate':evaluate(manifest,routing)
    elif args.phase=='replay':replay(manifest,routing)
if __name__=='__main__':main()
