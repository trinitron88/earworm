from records import read_lines,open_record
import json,hashlib,math,base64
from pathlib import Path
from collections import Counter,defaultdict
HERE=Path(__file__).resolve().parent
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
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
def replay(frames,cfg,q,offset):
    start=offset;label=None;pending=[];out=[]
    for f in frames:
        pitch=f['pitch_semitones'];same=(pitch is None and label is None) or (pitch is not None and label is not None and abs(pitch-label)<q['pitch_change'])
        if same:pending=[];continue
        if pending:
            prev=pending[-1]['pitch_semitones'];same=(pitch is None and prev is None) or (pitch is not None and prev is not None and abs(pitch-prev)<q['pitch_change'])
            if not same:pending=[]
        pending.append(f)
        if len(pending)<(8 if pitch is None else q['confirm']):continue
        end=max(start,pending[0]['end_sample']-cfg['window_samples']//2)
        if end-start>=256:out.append((start,end,((f['end_sample']+1023)//1024)*1024,label))
        start=end;label=pitch;pending=[]
    return out

def numerical_equal(a,b):
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(numerical_equal(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):return set(a)==set(b) and all(numerical_equal(a[k],b[k]) for k in a)
    if isinstance(a,(int,float)) and not isinstance(a,bool):return a==b or abs(a-b)<=1e-12
    return a==b

def main(split):
    d=HERE/'data'/split;cfg=json.loads((d/'config_used.json').read_text());truth={r['episode']:r for r in map(json.loads,read_lines(d/'truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(d/'cache.jsonl.gz')));waves={r['episode']:r for r in map(json.loads,read_lines(d/'wave_archive.jsonl.gz'))};records=list(map(json.loads,read_lines(d/'events.jsonl.gz')));checks={};previous='0'*64;by=defaultdict(list)
    for i,v in enumerate(records,1):
        r=v['record'];assert r['seq']==i and r['previous_sha256']==previous and digest(canonical(r).encode())==v['sha256'];previous=v['sha256'];by[r['episode']].append(r)
    checks['hash_chain']=True;maxerror=0.;count=0;maxchunks=0;maxeventdelay=0.;maxpayload=0;maxraw=0
    from scoring import measure,safe,selftest
    assert all(selftest().values());checks['scorer_edge_cases']=True
    for x in cache:
        eid=x['episode'];t=truth[eid];r=by[eid];raw=base64.b64decode(waves[eid]['prefix_b64']);future=base64.b64decode(waves[eid]['future_b64']);pred=x['operational'];maxraw=max(maxraw,len(raw));maxpayload=max(maxpayload,len(canonical(pred).encode()))
        assert len(raw)//4==t['arrived_samples']<=32000 and len(raw)%4096==0 and len(future)<=128000
        fc=next(v for v in r if v['kind']=='forecast_commit');oc=next(v for v in r if v['kind']=='oracle_boundary_forecast_commit');rv=next(v for v in r if v['kind']=='reveal');assert fc['seq']<oc['seq']<rv['seq'];assert fc['monotonic_ns']<=oc['monotonic_ns']<=rv['monotonic_ns'];assert fc['payload']==pred and fc['forecast_sha256']==digest(canonical(pred).encode());assert r[0]['ready']['guard_probe_blocked'];assert pred['guard_blocked_events']==['open']
        arrivals=[v for v in r if v['kind']=='arrival'];assert len(arrivals)==pred['chunk_count']<=32;maxchunks=max(maxchunks,len(arrivals));assert pred['evictions']==0 and pred['arrived_samples']==len(raw)//4
        for j,v in enumerate(arrivals):assert v['offset']==1024*j and v['wave_sha256']==digest(raw[j*4096:(j+1)*4096]) and v['input_fields']==['op','samples_b64'] and v['response']['evictions']==0
        dispatch={v['offset']:v for v in r if v['kind']=='chunk_dispatch'}
        if split=='heldout':
            assert len(dispatch)==len(arrivals)
            for item in pred['frames']+[e for ev in pred['events'].values() for e in ev]:
                chunk=(item['available_sample']//1024-1)*1024
                assert dispatch[chunk]['monotonic_ns']<=item['computed_monotonic_ns']<=arrivals[chunk//1024]['monotonic_ns']
        assert pred['chunk_hashes']==[v['wave_sha256'] for v in arrivals];offset=t['reset_sample'] or 0;assert pred['buffer_offset']==offset and pred['raw_buffer_samples']==len(raw)//4-offset and pred['raw_buffer_sha256']==digest(raw[offset*4:])
        assert all(f['end_sample']<=f['available_sample']<=len(raw)//4 and f['end_sample']-f['start_sample']==512 for f in pred['frames'])
        for name,ev in pred['events'].items():
            assert len(ev)<=32
            if name==cfg['selected']:
                q=next(q for q in cfg['boundary_grid'] if q['id']==name);expected=replay(pred['frames'],cfg,q,offset);actual=[(e['start_sample'],e['end_sample'],e['available_sample'],e['state_pitch']) for e in ev];assert expected==actual
            for e in ev:
                assert offset<=e['start_sample']<e['end_sample']<=e['available_sample']<=len(raw)//4;support=e.get('support');lo=support['start_sample'] if support else e['start_sample'];hi=support['end_sample'] if support else e['end_sample'];assert e['observation']['wave_sha256']==digest(raw[lo*4:hi*4]);maxeventdelay=max(maxeventdelay,(e['available_sample']-e['end_sample'])/16000)
        for name,ev in pred['events'].items():
            if name not in pred['support_policies_active']:continue
            originals=pred['events'][cfg['selected']];assert len(ev)==len(originals)
            policy=next(z for z in cfg['support_grid'] if z['id']==name)
            for index,e in enumerate(ev):
                orig=originals[index];assert e['original_event_index']==index and e['start_sample']==orig['start_sample'] and e['end_sample']==orig['end_sample'] and e['state_pitch']==orig['state_pitch'];assert e['original_observation_sha256']==digest(canonical(orig['observation']).encode());assert e['computed_monotonic_ns']>=orig['computed_monotonic_ns']
                support=e['support']
                if support:
                    assert support['start_sample']==e['start_sample']+policy['trim_samples'] and support['end_sample']==e['end_sample']-policy['trim_samples'];assert support['end_sample']-support['start_sample']>=512 and support['wave_sha256']==digest(raw[support['start_sample']*4:support['end_sample']*4])
                if e['measurement_available']:assert support and support['cycles']>=4 and e['observation']['pitch_semitones'] is not None
                else:assert e['observation']['pitch_semitones'] is None
        from validation_math import distribution,mix
        for policy in cfg['aggregation_grid']:
            name=policy['id']
            if name not in pred['aggregation_policies_active']:continue
            originals=pred['events'][cfg['selected']]
            assert len(pred['events'][name])==len(originals)
            for i,e in enumerate(pred['events'][name]):
                orig=originals[i];assert e['original_event_index']==i and e['original_observation_sha256']==digest(canonical(orig['observation']).encode())
                assert (e['start_sample'],e['end_sample'],e['state_pitch'])==(orig['start_sample'],orig['end_sample'],orig['state_pitch'])
                expected=[(lo,lo+sz) for sz in policy['windows'] for lo in range(e['start_sample']+128,e['end_sample']-128-sz+1,128)]
                assert [(w['start_sample'],w['end_sample']) for w in e['windows']]==expected
                for w in e['windows']:
                    assert w['observation']['wave_sha256']==digest(raw[w['start_sample']*4:w['end_sample']*4])
                    assert orig['computed_monotonic_ns']<=w['computed_monotonic_ns']<=e['computed_monotonic_ns']
                    assert w['end_sample']<=w['available_sample']==e['available_sample']
                cs,u,point=distribution(e['windows'],e['state_pitch'],cfg);assert numerical_equal(cs,e['distribution']['candidates']) and abs(u-e['distribution']['unknown_mass'])<=1e-12 and numerical_equal(point,e['observation']['pitch_semitones'])
            assert pred['events'][name]==pred['events'][name+'_mixture']
        for key,frames in pred.get('lattice',{}).items():
            q=next(q for q in cfg['lattice_grid'] if q['id']==key);assert len(frames)<=256
            assert [z['end_sample'] for z in frames]==list(range(offset+q['samples'],len(raw)//4+1,q['hop']))
            for z in frames:
                assert z['end_sample']-z['start_sample']==q['samples'] and z['observation']['wave_sha256']==digest(raw[z['start_sample']*4:z['end_sample']*4])
                assert z['end_sample']<=z['available_sample']<=len(raw)//4
                chunk=(z['available_sample']//1024-1)*1024;assert dispatch[chunk]['monotonic_ns']<=z['computed_monotonic_ns']<=arrivals[chunk//1024]['monotonic_ns']
                assert abs(sum(z['spectral_shape'])-1)<1e-9 or z['observation']['rms']<1e-8
                assert abs(z['pitch_distribution']['probability']+z['pitch_distribution']['unknown_mass']-1)<1e-12
        for b in t['bounds']:assert digest(raw[b['start']*4:b['end']*4])==b['wave_sha256']
        outputs={**pred['forecasts'],'oracle-boundary':x['oracle_forecasts']};events={**pred['events'],'oracle-boundary':x['oracle_events']};assert oc['forecasts']==x['oracle_forecasts'];scored=next(v['scores'] for v in r if v['kind']=='score')
        for front,fs in outputs.items():
            h=[e['observation'] for e in (pred['lattice'][front] if front in pred.get('lattice',{}) else events[front])]
            while h and h[-1]['pitch_semitones'] is None:h.pop()
            for name,f in fs.items():
                mc=dict(cfg['reference']);source=name
                if name.startswith('transition'):source='transition';mc['transition_order']=int(name[-1])
                elif name=='absolute':source='retrieval_absolute';mc['retrieval_absolute_order']=3
                elif name=='reference':source='retrieval_transposed'
                hh=h or [{'pitch_semitones':None}]
                if front in pred.get('lattice',{}) and name in ['absolute','reference','single']:
                    from lattice_validation import verify_readout
                    p,point=verify_readout(pred['lattice'][front],cfg,name,f);atoms=f['lookup_evidence']
                else:p,point,atoms=reconstruct(hh,source,mc)
                if front.endswith('_mixture'):p,point=mix(events[front],cfg,name,reconstruct);atoms=[]
                err=max(abs(a-b) for a,b in zip(p,f['probabilities']));assert err<1e-12;maxerror=max(maxerror,err);assert point==f['point_pitch_semitones'] or (point is not None and f['point_pitch_semitones'] is not None and abs(point-f['point_pitch_semitones'])<1e-12);assert len(atoms)==len(f['lookup_evidence']);assert numerical_equal(safe(measure(f,t)),scored[front][name]);count+=1
    for eid,t in truth.items():
        if t['variant']!=0:continue
        other=truth[eid[:-1]+'1'];assert Counter(b['wave_sha256'] for b in t['bounds'])==Counter(b['wave_sha256'] for b in other['bounds']);a=base64.b64decode(waves[eid]['prefix_b64']);b=base64.b64decode(waves[other['episode']]['prefix_b64']);assert len(a)==len(b);assert a[t['probe_start']*4:]==b[other['probe_start']*4:]
        if t['condition'] in ['removal','ambiguous']:assert a==b
        if t['condition']=='reset':assert a[t['reset_sample']*4:]==b[t['reset_sample']*4:]
        if t['condition']=='swap':
            for v in [0,1]:
                sx=truth[eid[:-1]+str(v)];ix=truth[f"{t['group']}/joint/intact/{1-v}"];assert waves[sx['episode']]['prefix_b64']==waves[ix['episode']]['prefix_b64'] and sx['pitch_semitones']==ix['pitch_semitones']
    inv=json.loads((d/'future_invariance.json').read_text());groups={t['group'] for t in truth.values()};assert len(inv)==4*len(groups) and all(x['same_forecast_bytes'] and x['first_future_sha256']!=x['other_future_sha256'] for x in inv)
    manifest=json.loads((HERE/'split_manifest.json').read_text());identities=[tuple(g['normalized_identity']) for g in manifest['groups']];excluded={tuple(x) for x in json.loads((HERE/'excluded_prior_motifs.json').read_text())};assert len(set(identities))==40 and not(set(identities)&excluded)
    historical=HERE.parent/'continuous-isolated-voice-v1';assert (HERE/'historical_front.py').read_bytes()==(historical/'model.py').read_bytes();oldcfg=json.loads((historical/'frozen_model.json').read_text());assert all(cfg[k]==v for k,v in oldcfg.items());previous_pkg=HERE.parent/'fundamental-observation-repair-v1';assert (HERE/'accepted_adapter.py').read_bytes()==(previous_pkg/'model.py').read_bytes();assert (HERE/'reference_model.py').read_bytes()==(previous_pkg/'reference_model.py').read_bytes();assert cfg['adapter']==json.loads((previous_pkg/'frozen_model.json').read_text())['adapter'];assert cfg['reference']==json.loads((HERE/'reference_config.json').read_text())
    assert (HERE/'trim_front.py').read_bytes()==(HERE.parent/'event-window-repair-v1/model.py').read_bytes()
    historical=json.loads((HERE/'prior_artifact_hashes.json').read_text());assert all(digest((HERE.parent.parent/n).read_bytes())==h for n,h in historical.items());assert sum(x['allocated_streams'] for x in json.loads((HERE/'run_ledger.json').read_text()))<=960;assert sum(x.stat().st_size for x in HERE.rglob('*') if x.is_file())<2*1024**3
    restores=json.loads((d/'save_restore.json').read_text());assert len(restores)==len(groups) and all(v['same_forecast_bytes'] for v in restores)
    assert (HERE/'aggregation_front.py').read_bytes()==(HERE.parent/'causal-event-aggregation-v1/model.py').read_bytes()
    assert json.loads((HERE/'preflight_result.json').read_text())['all_pass']
    assert (HERE/'model.py').read_bytes()==(HERE.parent/'causal-frame-lattice-v1/model.py').read_bytes()
    checks.update(guarded_preflight=True,scientific_model_unchanged=True,save_restore_determinism=True,fixed_cadence_lattice=True,independent_alignment_arithmetic=True,prefix_only_guard=True,pre_reveal_commitment=True,independent_event_replay=True,independent_retrieval_and_saved_scores=True,future_invariance=True,paired_bytes_inventory_probe=True,control_semantics=True,fresh_groups=True,frozen_observation_and_reference=True,prior_artifacts=True,capacity_and_storage=True,full_original_observations_and_support_provenance=True,independent_aggregation_and_mixture=True)
    if split=='heldout':
        freeze=json.loads((HERE/'freeze.json').read_text());receipt=json.loads((HERE/'preregistration_receipt.json').read_text());started=json.loads((d/'STARTED.json').read_text());from datetime import datetime
        assert datetime.fromisoformat(receipt['created_at'].replace('Z','+00:00')).timestamp()*1e9<started['start_utc_ns'] and started['frozen_inputs_match_commit'];assert all(digest((HERE/n).read_bytes())==h for n,h in freeze['files'].items());checks['preregistered_inputs']=True
    result=dict(all_pass=all(checks.values()),checks=checks,records=len(records),forecasts=count,maximum_reconstruction_error=maxerror,future_probes=len(inv),historical_files=len(historical),maximum_chunks=maxchunks,maximum_raw_prefix_bytes=maxraw,maximum_serialized_listener_payload_bytes=maxpayload,maximum_inferred_event_decision_delay_s=maxeventdelay,storage_note='Payload counts serialized events/frame-cache/forecasts/hashes, not Python heap/RSS. Raw buffer separately bounded. Multiple dev-grid fronts are counted together; evaluator archive is inaccessible.')
    (HERE/'validation').mkdir(exist_ok=True);(HERE/'validation'/f'{split}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
    import sys;main(sys.argv[1])
