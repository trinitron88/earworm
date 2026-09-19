"""Read-only audit of Experiment08 artifacts; no predictor changes or retuning.

Some checks deliberately recompute from PCM. Diagnostic ranking/known-reference
metrics are post-hoc descriptions of the frozen predictions, not new methods.
"""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from scipy.io import wavfile
from accounts_reader import evidence,score,decide,description_digest,events
from remember_changes_acoustics import describe_audio
from accounts_experiment import strict_account
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'accounts_results'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,v):(OUT/name).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    manifest=load(ROOT/'accounts_stimuli/manifest.json');config=load(OUT/'frozen_config.json');protocol=load(OUT/'protocol.json');dev=load(OUT/'development_pairs.json');pairs=load(OUT/'held_out_pairs.json');rows=load(OUT/'trials.json');details=load(OUT/'query_details.json');timings=load(ROOT/'accounts_features/timings.json');B={b['id']:b for b in manifest['blocks']};G={g['id']:g for g in manifest['groups']}
    checks={};before=load(OUT/'prior_files_before.json')['files'];changed=[p for p,h in before.items() if not (ROOT.parent/p).exists() or sha(ROOT.parent/p)!=h];assert not changed
    checks['earlier_files_unchanged']=len(before);checks['changed_prior_files']=changed
    assert all(sha(ROOT/n)==v for n,v in protocol['source_sha256'].items()) and config['source_sha256']==protocol['source_sha256'];checks['frozen_sources_unchanged']=True
    patterns=[tuple(p) for g in manifest['groups'] for p in g['base_patterns']];assert len(patterns)==len(set(patterns))==264 and not set(patterns)&{tuple(p) for p in manifest['excluded_patterns']};checks['fresh_disjoint_patterns']=264
    sets={s:{tuple(p) for g in manifest['groups'] if g['split']==s for p in g['base_patterns']} for s in ('fit','calibration','held_out')};assert not sets['fit']&sets['calibration'] and not sets['fit']&sets['held_out'] and not sets['calibration']&sets['held_out'];checks['split_patterns_disjoint']=True
    read={};wavehashes=[]
    for bid,b in B.items():
        sr,a=wavfile.read(b['audio_path']);assert sr==24000 and a.shape==(48000,) and a.dtype==np.float32 and np.isfinite(a).all()
        assert hashlib.sha256(a.tobytes()).hexdigest()==b['audio_sha256'];wavehashes.append(bid)
        if bid in timings:
            with np.load(ROOT/'accounts_features'/f'{bid}.npz',allow_pickle=False) as z:d={k:z[k] for k in z.files}
            assert description_digest(d)==timings[bid]['description_digest'];assert timings[bid]['pcm_sha256']==b['audio_sha256'];read[bid]=d
    checks['pcm_hashes_verified']=len(wavehashes);checks['description_digests_verified']=len(read)
    frozen=datetime.fromisoformat(config['frozen_utc']);pre=datetime.fromisoformat(protocol['frozen_utc'])
    assert all(datetime.fromisoformat(v['wall_start_utc'])>pre for v in timings.values())
    assert all(datetime.fromisoformat(v['wall_start_utc'])>frozen for bid,v in timings.items() if B[bid]['split']=='held_out')
    assert all(datetime.fromisoformat(v['wall_ready_utc'])<frozen for bid,v in timings.items() if B[bid]['split']!='held_out')
    assert not any(B[bid]['phase']=='stack' for bid in dev);checks['freeze_before_heldout_extraction']=True;checks['no_stacks_in_fitting_or_calibration']=True
    # Independent reconstruction of supervised matrix and coefficient fit.
    x=[];y=[]
    for bid,q in B.items():
        if q['role']!='query' or q['split']!='fit' or q['phase']!='core':continue
        g=G[q['group_id']]
        for rid in [g['reference_a_id'],g['reference_b_id']]+g['distractor_ids']:
            x.append(dev[bid][rid]['evidence']['features']);y.append(int(rid==q['reference_id']))
    scaler=StandardScaler().fit(x);model=LogisticRegression(C=1,class_weight='balanced',random_state=8,max_iter=2000).fit(scaler.transform(x),y)
    assert np.allclose(model.coef_[0],config['coef'],atol=1e-12) and abs(float(model.intercept_[0])-config['intercept'])<1e-12
    checks['fit_reproduced_pairs']=len(y)
    def val(v,method):
        if method=='accounts':return float(np.dot((np.array(v['evidence']['features'])-config['mean'])/config['scale'],config['coef'])+config['intercept']) if v['evidence']['available'] else -1e6
        return v[method]
    cal=[]
    for q in B.values():
        if q['role']=='query' and q['split']=='calibration' and q['phase']=='core':
            g=G[q['group_id']];other=g['reference_b_id'] if q['source']=='a' else g['reference_a_id'];cal.append((q,[q['reference_id']]+g['distractor_ids'],[other]+g['distractor_ids']))
    for method in ('accounts','count','envelope'):
        levels=sorted({val(dev[q['id']][i],method) for q,pos,neg in cal for i in set(pos+neg)});levels.append(float(np.nextafter(levels[-1],np.inf)));options=[]
        for t in levels:
            hit=false=0
            for q,pos,neg in cal:
                selected=[i for i in pos if val(dev[q['id']][i],method)>=t];hit+=selected==[q['reference_id']];false+=any(val(dev[q['id']][i],method)>=t for i in neg)
            if false<=.05*len(cal):options.append((hit,-false,t))
        best=max(options);expected=config['calibration'][method];assert best==(expected['correct_singletons'],-expected['false_acceptances'],expected['threshold'])
    checks['calibration_selection_recomputed']=True
    for r in rows:
        q=B[r['query_id']];g=G[r['group_id']];tail=g['distractor_ids'] if r['delay_s'] else [];other=g['reference_b_id'] if q['source']=='a' else g['reference_a_id'];pos=[q['reference_id']]+tail;neg=[other]+tail
        if r['mode']=='drop_reference':pos=tail.copy();neg=tail.copy()
        if r['mode']=='reset_before_query':pos=[];neg=[]
        if r['method']=='old07':choose=lambda ids:[i for i in ids if pairs[q['id']][i]['old07']]
        else:
            t=config['threshold'] if r['method']=='accounts' else config['baseline_thresholds'][r['method']]
            choose=lambda ids:[i for i in ids if val(pairs[q['id']][i],r['method'])>=t]
        a,b=choose(pos),choose(neg)
        assert a==r['accepted_present'] and b==r['accepted_absent'];assert r['correct_singleton']==(a==[q['reference_id']]);assert r['source_covered']==(q['reference_id'] in a);assert r['absent_false_accept']==bool(b)
    checks['trial_rows_recomputed']=len(rows)
    for d in details:
        for accepted in d['accepted']:
            for p in accepted['accounts']:
                for gap in p['missing_evidence']:assert gap['physical_cause']=='not_identified'
    checks['no_physical_cause_assertions']=True
    # Selected independent waveform reruns plus opaque-handle renaming and order checks.
    recomputed=[]
    for gid,family in [('e08','delete_rest'),('e09','mask_present'),('e10','delete_timing'),('e11','delete_detune')]:
        g=G[gid];q=next(b for b in B.values() if b['group_id']==gid and b['family']==family and b['source']=='a' and b['role']=='query');rid=q['reference_id'];sr,pcm=wavfile.read(q['audio_path']);qd=describe_audio(pcm,sr);sr,pcm=wavfile.read(B[rid]['audio_path']);rd=describe_audio(pcm,sr)
        assert description_digest(qd)==description_digest(read[q['id']]) and description_digest(rd)==description_digest(read[rid]);ev=evidence(rd,qd);assert ev==pairs[q['id']][rid]['evidence']
        mem=[(i,read[i]) for i in [rid]+g['distractor_ids']];decision=decide(mem,qd,config);renamed=[(str(k),d) for k,(h,d) in enumerate(mem)];new=decide(list(reversed(renamed)),qd,config)
        expected={str(k):v for k,(h,d) in enumerate(mem) for v in decision['candidates'] if v['handle']==h}
        assert set(expected)=={v['handle'] for v in new['candidates']}
        for v in new['candidates']:assert v['accounts']==expected[v['handle']]['accounts'] and v['support_logit']==expected[v['handle']]['support_logit']
        recomputed.append(q['id'])
    checks['fresh_pair_and_handle_invariance_checks']=recomputed
    replays=load(OUT/'fresh_replays.json');swapped=load(OUT/'swapped_replays.json');prefix=load(OUT/'prefix_checks.json')
    for r in replays+swapped:
        assert not r['feature_cache_hit'] and not r['similarity_cache_hit'];assert r['decision_available_s']>=r['query_description_ready_s']>=r['query_audio_complete_s'];assert datetime.fromisoformat(r['wall_decision_ready_utc'])>=datetime.fromisoformat(r['wall_query_compute_start_utc'])
        expected=next(x for x in rows if x['query_id']==r['query_id'] and x['mode']==r['mode'] and x['delay_s']==16 and x['method']=='accounts')['accepted_absent' if r in swapped else 'accepted_present'];assert [v['handle'] for v in r['decision']['candidates']]==expected
    assert all(r['emitted_decision_equal'] for r in prefix);checks['fresh_decisions_equal_batch']=len(replays)+len(swapped);checks['availability_checks_pass']=True;checks['future_prefix_pairs']=len(prefix)
    # Post-hoc diagnostics do NOT influence prediction or the frozen thresholds.
    diagnostic={};primary=[r for r in rows if r['method']=='accounts' and r['mode']=='intact' and r['delay_s']==16]
    for family in manifest['core_families']+manifest['stack_order']:
        rr=[r for r in primary if r['family']==family];d=dict(n=len(rr),unique_top_score_true=0,true_top_tied=0,direct_best_alignment=0,direct_account_set=0,top_true_but_rejected=0,accepted_singleton=0)
        for r in rr:
            q=B[r['query_id']];g=G[q['group_id']];rid=q['reference_id'];scores={i:val(pairs[q['id']][i],'accounts') for i in [rid]+g['distractor_ids']};maximum=max(scores.values());top=[i for i,v in scores.items() if abs(v-maximum)<1e-9];correct=top==[rid]
            d['unique_top_score_true']+=correct;d['true_top_tied']+=rid in top and len(top)>1;d['top_true_but_rejected']+=correct and not r['correct_singleton'];d['accepted_singleton']+=r['correct_singleton'];pp=pairs[q['id']][rid]['evidence']['paths']
            d['direct_best_alignment']+=bool(pp) and strict_account(pp[0],B[rid],q,read[rid],read[q['id']]);d['direct_account_set']+=any(strict_account(p,B[rid],q,read[rid],read[q['id']]) for p in pp)
        diagnostic[family]=d
    dump('posthoc_diagnostics.json',dict(label='Post-hoc fixed-output diagnostics; no new fitting or threshold selection. Known-reference alignment ceilings use an oracle source and are not joint retrieval results.',families=diagnostic))
    checks['diagnostic_source']='Known-reference ceilings separated from actually retrieved joint metric.'
    dump('audit.json',checks);dump('prior_files_after.json',dict(files=before,unchanged_count=len(before),changed=[]))
    print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
