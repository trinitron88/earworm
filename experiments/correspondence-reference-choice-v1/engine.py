"""Label-free clean-observation worker. No model, score archive or generator access."""
import base64, builtins, hashlib, io, json, os, resource, socket, sys, time
from collections import deque
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent/'historical'))
from listener import predict as historical_predict
from global_matcher import predict as global_predict

def encode(state):
    buf=io.BytesIO(); np.savez_compressed(buf,**state)
    return base64.b64encode(buf.getvalue()).decode()

def decode(blob):
    with np.load(io.BytesIO(base64.b64decode(blob)),allow_pickle=False) as z:
        return {k:z[k].copy() for k in z.files}

def deep_bytes(obj, seen=None):
    seen=set() if seen is None else seen
    if id(obj) in seen:return 0
    seen.add(id(obj)); n=sys.getsizeof(obj)
    if isinstance(obj,dict):n+=sum(deep_bytes(k,seen)+deep_bytes(v,seen) for k,v in obj.items())
    elif isinstance(obj,(list,tuple,deque)):n+=sum(deep_bytes(v,seen) for v in obj)
    return n

def state_from_units(records, exact=False):
    out={k:np.concatenate([r[k] for r in records]) for k in ['t','unit','rms','clean','available_at']}
    if not exact:return out
    units=[int(r['unit'][0]) for r in records]
    segments=[]
    for u in units:
        if segments and segments[-1][1]==u:segments[-1][1]=u+1
        else:segments.append([u,u+1])
    ev=[];lc=[];rc=[]
    for r in records:
        for e,l,rr in zip(r['events'],r['event_left_clipped'],r['event_right_clipped']):
            # Only reconnect edges explicitly clipped by arrival, not same-pitch onsets.
            if ev and rc[-1] and l and abs(ev[-1][1]-e[0])<1e-9 and ev[-1][2]==e[2]:
                ev[-1][1]=float(e[1]);rc[-1]=bool(rr)
            else:ev.append(e.tolist());lc.append(bool(l));rc.append(bool(rr))
    out.update(events=np.asarray(ev,dtype=float).reshape(-1,3),event_left_clipped=np.asarray(lc),event_right_clipped=np.asarray(rc),segments=np.asarray(segments,dtype=float))
    return out

def predict(state,method):
    if method!='D':return global_predict(state,exact=method=='G-exact')
    raw=historical_predict(state,'ceiling');h=raw.get('hypothesis')
    accepted=h is not None and raw['distance']<=0.0
    selected=None
    if h:
        selected={**h,'center':(h['start']+h['end'])/2,'scale':h['stretch'],
                  'scale_range':None,'shift_range':[h['shift'],h['shift']]}
    pairs=h.get('path',[]) if h else []
    loud=np.flatnonzero(state['rms']>1e-4)
    qi=np.flatnonzero((state['t']>state['t'][loud[-1]]-2+1e-8)&(state['t']<=state['t'][loud[-1]]+1e-8)) if len(loud) else []
    return {'accepted':accepted,'selected':selected if accepted else None,'candidate_best':selected,
            'candidates':[] if selected is None else [selected],
            'reason':'historical_zero_distance_acceptance' if accepted else 'historical_rejection',
            'query_support':raw.get('query_support'), 'raw_historical':raw,
            'coverage':{'query_rows':len(qi),'charged_query_rows':len(set(p[0] for p in pairs)),
                        'skipped_query_rows':len(qi)-len(set(p[0] for p in pairs)),
                        'full_consistency_verified':False}}

def install_guard():
    def denied(*a,**k):raise PermissionError('predictor filesystem/network access disabled')
    builtins.open=denied;io.open=denied;os.open=denied;socket.socket=denied

def main():
    method=sys.argv[1];assert method in ['D','G','G-exact'];install_guard()
    records=[];ring=deque(maxlen=4);arrivals=[];peak=0;replacements=0
    print(json.dumps({'ready':True,'method':method,'guard':True}),flush=True)
    for line in sys.stdin:
        cmd=json.loads(line)
        if cmd['op']=='arrive':
            rec=decode(cmd['blob']);u=int(rec['unit'][0]);assert len(rec['t'])==10
            assert np.all(rec['unit']==u) and np.all(rec['available_at']==u+1)
            assert np.all(rec['t']<u+1) and (not records or u==int(records[-1]['unit'][0])+1)
            assert np.allclose(rec['t'],u+np.arange(10)*.1+.05,rtol=0,atol=1e-10)
            assert rec['clean'].shape==(10,129) and np.isfinite(rec['clean']).all()
            assert np.isin(rec['clean'],[0,1]).all() and np.all(rec['clean'].sum(axis=1)==1)
            assert np.array_equal(rec['rms'],1-rec['clean'][:,128])
            assert method=='G-exact' or 'events' not in rec
            if method=='G-exact':
                e=rec['events'];assert e.ndim==2 and e.shape[1]==3 and np.isfinite(e).all()
                assert np.all(e[:,0]>=u) and np.all(e[:,1]<=u+1) and np.all(e[:,1]>e[:,0])
                assert np.all(e[1:,0]>=e[:-1,1]-1e-10) and np.all((e[:,2]>=0)&(e[:,2]<128)&(e[:,2]==np.floor(e[:,2])))
            records.append(rec);ring.append(rec)
            if len(records)>60:records.pop(0);replacements+=1
            stored=deep_bytes([records,ring]);peak=max(peak,stored);assert stored<=8*1024**2
            row={'unit':u,'simulated_available_at':u+1,'received_monotonic':time.monotonic(),
                 'recent_units':[int(r['unit'][0]) for r in ring], 'persistent_units':len(records),
                 'persistent_bytes':stored,'observation_sha256':hashlib.sha256(rec['clean'].tobytes()).hexdigest()}
            print(json.dumps(row),flush=True);del rec,cmd,line,row
        elif cmd['op']=='predict':
            mode=cmd['mode'];removed=set(cmd.get('remove_units',[]))
            assert mode in ['full','recent','removed']
            kept=[r for r in (ring if mode=='recent' else records) if int(r['unit'][0]) not in removed]
            # Destructive control in a one-readout process: remove original storage too.
            records=kept;ring=deque([r for r in ring if int(r['unit'][0]) in {int(k['unit'][0]) for k in kept}],maxlen=4)
            state=state_from_units(kept,method=='G-exact');statebytes=deep_bytes(state)
            total=deep_bytes([records,ring,state]);assert total<=8*1024**2
            began=time.monotonic();answer=predict(state,method);finished=time.monotonic()
            answer.update(method=method,mode=mode,compute_seconds=finished-began,
                prediction_finished_monotonic=finished,simulation_observations_available_at=int(records[-1]['unit'][0])+1,
                simulation_compute_only_finish=int(records[-1]['unit'][0])+1+(finished-began),
                predictor_accessible_state_bytes=total,retained_peak_bytes=peak,
                scratch_state_bytes=statebytes,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                kept_units=[int(r['unit'][0]) for r in kept],removed_units=sorted(removed),
                persistent_replacements=replacements,retained_observation_sha256=hashlib.sha256(state['clean'].tobytes()).hexdigest(),
                retained_timestamps_sha256=hashlib.sha256(state['t'].tobytes()).hexdigest())
            print(json.dumps(answer,allow_nan=False),flush=True);del answer,state,kept,cmd,line
            return
        else:raise ValueError(cmd['op'])

if __name__=='__main__':main()
