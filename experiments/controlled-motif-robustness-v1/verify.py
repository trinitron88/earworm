"""Saved-evidence validation; scalar independent retrieval/probability reconstruction."""
import json,hashlib,math
from pathlib import Path
from collections import Counter,defaultdict
HERE=Path(__file__).resolve().parent
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x).hexdigest()
def reconstruct(h,name,cfg):
    anchor=h[-1]['pitch_semitones'];prior=cfg['prior'];cal=cfg['calibration'][name];atoms=[]
    n=1 if name=='recency' else cfg.get(name+'_order',3)
    if name!='present' and anchor is not None and len(h)>=n+1:
        q=[x['pitch_semitones'] for x in h[-n:]]
        if None not in q:
          for start in range(len(h)-n):
            z=[x['pitch_semitones'] for x in h[start:start+n+1]]
            if None in z:continue
            shift=sum(a-b for a,b in zip(q,z[:-1]))/n if name=='retrieval_transposed' else 0.
            dist=max(abs(b+shift-a) for a,b in zip(q,z[:-1]));interval=z[-1]+shift-anchor
            if dist<=cfg.get(name+'_cutoff',.3):atoms.append(dict(distance=dist,interval=interval,source_start=start))
        if name=='recency':atoms=atoms[-1:]
    if anchor is None:p=[0.]*49+[1.]
    else:
        p=prior.copy() if not atoms else [0.]*50
        if atoms:
            weights=[math.exp(-a['distance']/cal['temperature']) for a in atoms];sw=sum(weights)
            for a,w in zip(atoms,weights):
                v=a['interval']
                if not -24.5<=v<=24.5:p[-1]+=w/sw;continue
                masses=[math.exp(-.5*((k-v)/cal['sigma'])**2) for k in range(-24,25)];sm=sum(masses)
                if sm==0:p[-1]+=w/sw
                else:
                    for j,m in enumerate(masses):p[j]+=w/sw*m/sm
        p=[(1-cal['floor'])*v+cal['floor']/50 for v in p];sp=sum(p);p=[v/sp for v in p]
    mode=max(range(50),key=p.__getitem__);point=None if mode==49 or anchor is None else anchor+mode-24
    return p,point,atoms
def main(split):
    data=HERE/'data'/split;cfg=json.loads((data/'config_used.json').read_text());truth={x['episode']:x for x in map(json.loads,(data/'truth.jsonl').read_text().splitlines())};cache=list(map(json.loads,(data/'arrived_cache.jsonl').read_text().splitlines()))
    manifest=json.loads((HERE/'split_manifest.json').read_text())['groups'];checks={}
    checks['split_groups_unique']=len({g['group_id'] for g in manifest})==40 and len({tuple(g['motif']) for g in manifest})==40 and len({g['seed'] for g in manifest})==40
    prior=HERE.parent/'history-prediction-v1'
    checks['exact_reference_code']=digest((HERE/'reference_model.py').read_bytes())==digest((prior/'model.py').read_bytes())
    checks['exact_reference_config']=cfg['reference']==json.loads((prior/'frozen_model.json').read_text())
    records=[json.loads(s) for s in (data/'events.jsonl').read_text().splitlines()];previous='0'*64;episodes=defaultdict(list)
    for i,v in enumerate(records,1):
        r=v['record'];assert r['seq']==i and r['previous_sha256']==previous and v['sha256']==digest(canonical(r).encode());previous=v['sha256'];episodes[r['episode']].append(r)
    checks['hash_chain']=True;maxdiff=0.;forecast_count=0
    for x in cache:
        eid=x['episode'];t=truth[eid];rs=episodes[eid];kinds=[r['kind'] for r in rs];fc=next(r for r in rs if r['kind']=='forecast_commit');rv=next(r for r in rs if r['kind']=='reveal')
        assert fc['seq']<rv['seq'] and fc['monotonic_ns']<=rv['monotonic_ns'] and rv['forecast_sequence']==fc['seq'];assert kinds.index('revealed_observation')>kinds.index('reveal')
        assert fc['payload']==x['forecast'];assert fc['forecast_bytes_sha256']==digest(canonical(x['forecast']).encode())
        arrivals=[r for r in rs if r['kind']=='arrival'];assert len(arrivals)==14
        assert all(r['input_fields']==['op','samples_b64'] and r['evictions']==0 and r['occupancy']<=32 for r in arrivals)
        assert all(r['monotonic_ns']<=fc['monotonic_ns'] for r in arrivals)
        assert all(r['observation']['sample_count']<=6400 for r in arrivals)
        assert [r['sample_sha256'] for r in arrivals]==t['prefix_wave_sha256']==[o['wave_sha256'] for o in x['observations']]
        assert rs[0]['worker_ready']['guard_probe_blocked'];assert x['forecast']['guard_blocked_events']==['open'];assert x['forecast']['arrivals']==14 and x['forecast']['evictions']==0
        h=x['observations'][11:] if t['condition']=='reset' else x['observations'];assert h==x['memory_at_forecast'];assert digest(canonical(h).encode())==x['forecast']['memory_sha256']
        assert digest(canonical(t['prefix_wave_sha256']).encode())==x['forecast']['prefix_sha256']
        for name,f in x['forecast']['forecasts'].items():
            source='retrieval_transposed' if name in ('reference','candidate') else name
            p,point,atoms=reconstruct(h,source,cfg['reference' if name=='reference' else 'new'])
            diff=max(abs(a-b) for a,b in zip(p,f['probabilities']));maxdiff=max(maxdiff,diff);assert diff<1e-12 and (point==f['point_pitch_semitones'] or (point is not None and f['point_pitch_semitones'] is not None and abs(point-f['point_pitch_semitones'])<1e-12));assert len(atoms)==len(f['lookup_evidence']);forecast_count+=1
            for a,b in zip(atoms,f['lookup_evidence']):assert a['source_start']==b['source_start'] and abs(a['distance']-b['distance'])<1e-12 and abs(a['interval']-b['interval'])<1e-12
    checks.update(prefix_only_api_and_guard=True,zero_eviction=True,availability_and_pre_reveal_commitment=True,independent_scalar_reconstruction=True)
    groups=sorted({t['group_id'] for t in truth.values()})
    for g in groups:
      for cell in ['matched','timbre','duration','joint']:
       for cond in (['intact','reset','removal','swap','shuffle','ambiguous'] if cell=='joint' else ['intact']):
        a,b=[truth[f'{g}/{cell}/{cond}/{v}'] for v in [0,1]]
        assert Counter(a['prefix_wave_sha256'])==Counter(b['prefix_wave_sha256']);assert a['prefix_wave_sha256'][-5:]==b['prefix_wave_sha256'][-5:]
        assert Counter(a['prefix_true_pitches'])==Counter(b['prefix_true_pitches'])
        if cond in ['reset','removal','ambiguous']:
            aa=next(x for x in cache if x['episode']==a['episode'])['memory_at_forecast'];bb=next(x for x in cache if x['episode']==b['episode'])['memory_at_forecast'];assert aa==bb
        if cond=='swap':
            for v,t in enumerate([a,b]):
                other=truth[f'{g}/joint/intact/{1-v}'];assert t['prefix_wave_sha256']==other['prefix_wave_sha256'] and t['pitch_semitones']==other['pitch_semitones']
        if cond=='ambiguous':assert a['outcome_probabilities']==b['outcome_probabilities']==[.5,.5] and a['pitch_semitones']!=b['pitch_semitones']
    checks.update(paired_byte_duration_energy_inventory_balance=True,identical_present=True,control_semantics=True)
    invariance=json.loads((data/'future_invariance.json').read_text());assert len(invariance)==4*len(groups) and all(x['same_forecast_bytes'] and x['first_future_sha256']!=x['substituted_future_sha256'] for x in invariance)
    checks['future_invariance']=True
    ledger=json.loads((HERE/'run_ledger.json').read_text());assert sum(x['allocated_streams'] for x in ledger)<=880
    assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())<2*1024**3;checks['stream_and_storage_budgets']=True
    if split=='heldout':
        frozen=json.loads((HERE/'freeze.json').read_text());receipt=json.loads((HERE/'preregistration_receipt.json').read_text());started=json.loads((data/'STARTED.json').read_text())
        from datetime import datetime
        assert datetime.fromisoformat(receipt['created_at'].replace('Z','+00:00')).timestamp()*1e9<started['start_utc_ns']
        for name,h in frozen['files'].items():assert digest((HERE/name).read_bytes())==h
        assert started['execution_inputs_match_commit'];checks['preregistered_frozen_evaluation']=True
    old=json.loads((HERE/'prior_artifact_hashes.json').read_text());root=HERE.parent.parent
    assert all(digest((root/name).read_bytes())==h for name,h in old.items());checks['prior_artifacts_unchanged']=True
    result=dict(all_pass=all(checks.values()),checks=checks,records=len(records),forecasts=forecast_count,maximum_reconstruction_error=maxdiff,future_invariance_probes=len(invariance),prior_files_verified=len(old),limitations='Python audit guard is instrumented isolation, not an adversarial OS sandbox. Byte-multiset identity implies identical total energy/duration/inventory. Timestamps report processing availability, not real-time audio latency.')
    (HERE/'validation').mkdir(exist_ok=True);(HERE/'validation'/f'{split}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
    import sys;main(sys.argv[1])
