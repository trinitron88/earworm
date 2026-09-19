"""Independent stdlib verification from saved observations/logs, no pipeline rerun."""
import argparse,collections,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
NAMES=['present','recency','transition','retrieval_absolute','retrieval_transposed','relational']
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]

def expected(history,name,cfg):
    anchor=history[-1]['pitch_semitones'];atoms=[]
    if anchor is None:return [0.]*49+[1.]
    k=1 if name=='recency' else cfg.get(name+'_order',3)
    q=[x['pitch_semitones'] for x in history[-k:]]
    if name!='present' and len(q)==k and all(x is not None for x in q):
        for start in range(len(history)-k):
            v=[x['pitch_semitones'] for x in history[start:start+k+1]]
            if any(x is None for x in v):continue
            old=v[:-1]
            if name in ('recency','transition','retrieval_absolute'):
                d=max(abs(a-b) for a,b in zip(old,q));interval=v[-1]-anchor
            elif name=='retrieval_transposed':
                shift=sum(b-a for a,b in zip(old,q))/k;d=max(abs(a+shift-b) for a,b in zip(old,q));interval=v[-1]+shift-anchor
            else:
                errors=[(old[j]-old[i])-(q[j]-q[i]) for i in range(k) for j in range(i+1,k)]
                d=math.sqrt(sum(x*x for x in errors)/len(errors));interval=v[-1]-old[-1]
            if d<=cfg.get(name+'_cutoff',.3):atoms.append((d,interval))
    if name=='recency' and atoms:atoms=atoms[-1:]
    cal=cfg.get('calibration',{}).get(name,{'temperature':.1,'sigma':.2,'floor':.01})
    p=[0.]*50
    if not atoms:p=list(cfg['prior'])
    else:
        weights=[math.exp(-d/cal['temperature']) for d,v in atoms];z=sum(weights)
        for (d,v),weight in zip(atoms,weights):
            w=weight/z
            if v< -24.5 or v>24.5:p[-1]+=w
            else:
                mass=[math.exp(-.5*((b-v)/cal['sigma'])**2) for b in range(-24,25)];norm=sum(mass)
                if not norm:p[-1]+=w
                else:
                    for j,m in enumerate(mass):p[j]+=w*m/norm
    p=[(1-cal['floor'])*v+cal['floor']/50 for v in p];norm=sum(p);return [v/norm for v in p]

def main(split):
    directory=HERE/'data'/split;truth={x['episode']:x for x in lines(directory/'truth.jsonl')};cache=lines(directory/'arrived_cache.jsonl');cfg=read(directory/'config_used.json')
    runtime=read(directory/'runtime.json');sources=read(directory/'execution_sources.json')
    assert sha(canon({name:sha(code.encode()) for name,code in sorted(sources.items())}).encode())==runtime['execution_code_sha256']
    manifest=read(HERE/'split_manifest.json');groups=[g for g in manifest['groups'] if g['split']==split]
    assert len({g['group_id'] for g in manifest['groups']})==len({g['seed'] for g in manifest['groups']})==36
    assert len(cache)==len(truth)==len(groups)*24
    events=lines(directory/'events.jsonl');previous='0'*64;per_episode=collections.defaultdict(list)
    for seq,entry in enumerate(events,1):
        r=entry['record'];assert r['seq']==seq and r['previous_sha256']==previous and sha(canon(r).encode())==entry['sha256'];previous=entry['sha256'];per_episode[r['episode']].append(r)
    max_error=0.;prediction_checks=0;targets=[]
    for c in cache:
        eid=c['episode'];t=truth[eid];ev=per_episode[eid];prefix=[x for x in ev if x['kind']=='arrival'];fc=next(x for x in ev if x['kind']=='forecast_commit');reveal=next(x for x in ev if x['kind']=='reveal');score=next(x for x in ev if x['kind']=='score');after=next(x for x in ev if x['kind']=='revealed_observation')
        assert len(prefix)==15 and [r['arrival_index'] for r in prefix]==list(range(15))
        assert prefix[-1]['seq']<fc['seq']<reveal['seq']<after['seq']<score['seq']
        assert all(r['input_fields']==['op','samples_b64'] and r['evictions']==0 and r['occupancy']<=32 for r in prefix)
        assert ev[0]['worker_ready']['guard_probe_blocked'] and fc['payload']['guard_blocked_events']==['open']
        assert c['observations']==[r['observation'] for r in prefix]
        assert all(o['duration_s']==.12 and o['sample_count']==1920 for o in c['observations'])
        hashes=[o['wave_sha256'] for o in c['observations']];assert hashes==t['prefix_wave_sha256']
        assert fc['payload']==c['forecast'] and fc['forecast_bytes_sha256']==sha(canon(c['forecast']).encode())
        assert fc['payload']['prefix_sha256']==sha(canon(hashes).encode())
        memory=c['observations'][-3:] if t['condition']=='reset' else c['observations']
        assert c['memory_at_forecast']==memory and fc['payload']['memory_sha256']==sha(canon(memory).encode())
        assert fc['payload']['occupancy']==len(memory) and fc['payload']['evictions']==0
        assert fc['payload']['arrivals']==15 and fc['payload']['deliberate_resets']==int(t['condition']=='reset')
        assert after['observation']==c['future_observation'] and after['observation']['wave_sha256']==reveal['future_sha256']==t['future_sha256']
        assert abs(c['future_observation']['pitch_semitones']-t['pitch_semitones'])<.35
        for o,pitch in zip(c['observations'],t['prefix_true_pitches']):
            if o['pitch_available']:assert abs(o['pitch_semitones']-pitch)<.35
            else:assert t['condition']=='removal'
        if t['family']=='transfer':
            assert t['target_never_in_prefix'] and t['future_sha256'] not in hashes
            assert min(abs(t['pitch_semitones']-o['pitch_semitones']) for o in c['observations'] if o['pitch_semitones'] is not None)>.35
            targets.append(t['pitch_semitones'])
        assert set(c['forecast']['forecasts'])==set(NAMES)
        for name,f in c['forecast']['forecasts'].items():
            pred=f['probabilities'];assert len(pred)==50 and min(pred)>=0 and abs(sum(pred)-1)<1e-12
            independent=expected(memory,name,cfg);error=max(abs(a-b) for a,b in zip(pred,independent));max_error=max(max_error,error);assert error<1e-10
            assert f['search_entries_examined']<=14
            mode=max(range(50),key=lambda i:pred[i]);assert f['point_interval_semitones']==(mode-24 if mode<49 else None)
            if mode<49:assert f['point_pitch_semitones']==f['anchor_semitones']+(mode-24)
            y=[0.]*50
            for v,m in zip(t['outcome_intervals'],t['outcome_probabilities']):y[round(v)+24]+=m
            s=score['scores'][name]
            assert abs(s['log_loss']+sum(a*math.log(b) for a,b in zip(y,pred)))<1e-12
            assert abs(s['brier']-sum((a-b)**2 for a,b in zip(pred,y)))<1e-12
            assert s['correct_within_tolerance']==(f['point_pitch_semitones'] is not None and abs(f['point_pitch_semitones']-t['pitch_semitones'])<=.35)
            prediction_checks+=1
    for g in groups:
        for family in ['basic','transfer']:
            for condition in ['intact','reset','removal','swap','shuffle','ambiguous']:
                a,b=[truth[f"{g['group_id']}/{family}/{condition}/{i}"] for i in [0,1]]
                assert collections.Counter(a['prefix_wave_sha256'])==collections.Counter(b['prefix_wave_sha256'])
                assert a['prefix_wave_sha256'][-3:]==b['prefix_wave_sha256'][-3:]
                if condition=='ambiguous':assert a['prefix_wave_sha256']==b['prefix_wave_sha256'] and a['outcome_probabilities']==b['outcome_probabilities']==[.5,.5]
                if condition=='swap':
                    for i in [0,1]:assert truth[f"{g['group_id']}/{family}/swap/{i}"]['pitch_semitones']==truth[f"{g['group_id']}/{family}/intact/{1-i}"]['pitch_semitones']
    inv=read(directory/'future_invariance.json');assert len(inv)==len(groups)*2
    for x in inv:
        assert x['same_forecast_bytes'] and x['first_future_sha256']!=x['substituted_future_sha256']
        fc=next(r for r in per_episode[x['episode']] if r['kind']=='forecast_commit');assert fc['forecast_bytes_sha256']==x['forecast_sha256']
    novelty_gap=None
    if split=='heldout':
        training=[]
        for part in ['development','calibration']:
            for row in lines(HERE/'data'/part/'arrived_cache.jsonl'):
                training.extend(o['pitch_semitones'] for o in row['observations']+[row['future_observation']] if o['pitch_semitones'] is not None)
        novelty_gap=min(abs(a-b) for a in targets for b in training);assert novelty_gap>.35
        frozen=read(HERE/'freeze.json');receipt=read(HERE/'preregistration_receipt.json')
        assert receipt['protocol_sha256']==frozen['files']['protocol.json']
        assert runtime['execution_code_sha256']==frozen['execution_code_sha256'] and runtime['execution_inputs_match_commit'] is True
        assert receipt['posted_utc_ns']<read(directory/'STARTED.json')['start_utc_ns']
        for name,h in frozen['files'].items():assert sha((HERE/name).read_bytes())==h
    result={'status':'pass','split':split,'groups':len(groups),'episodes':len(cache),'forecasts_independently_reconstructed':prediction_checks,'max_probability_reconstruction_error':max_error,'hash_chain_records':len(events),'invariance_checks':len(inv),'transfer_min_distance_from_training_semitones':novelty_gap,
      'validity_gates':{'paired_bytes_inventory_duration':True,'identical_probe_and_final_history':True,'disjoint_group_seed_splits':True,'prefix_only_api_and_guard':True,'forecast_before_reveal':True,'future_invariance':True,'common_observation_budget':True,'no_eviction':True,'control_truth_semantics':True,'transfer_novelty':True},
      'named_decisions':{'causality':'Accept causal forecasts only if arrival ordering, prefix reconstruction, IPC schema and access guard reconcile; otherwise withhold causal claim.','balance_and_novelty':'Accept history/transfer comparison only if paired sound inventory, probe equality, split isolation and target novelty hold.','numerics':'Accept prediction scores only if independent probability and proper-score reconstruction agree.','limits':'This checks the instrumented implementation and saved trace, not an adversarial OS sandbox or human perceptual identity.'}}
    out=HERE/'validation';out.mkdir(exist_ok=True);(out/f'{split}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['development','calibration','heldout']);main(p.parse_args().split)
