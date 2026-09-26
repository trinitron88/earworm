"""Saved-input/package checks only; never imports or calls a matcher."""
import hashlib,json,pathlib,time
import numpy as np

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def canonical(arrays):
    h=hashlib.sha256()
    for k in sorted(arrays):
        a=np.ascontiguousarray(arrays[k]);h.update(k.encode());h.update(a.dtype.str.encode());h.update(json.dumps(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()
def validate(root):
    root=pathlib.Path(root);began=time.monotonic();old=root.parent/'correspondence-reference-choice-v1'
    methods={}
    for name in ['global_matcher.py','engine.py','fixtures.py','historical/listener.py','historical/matching.py']:
        methods[name]=sha(root/name);assert methods[name]==sha(old/name),name
    counts={};entries=[];seen=set();planned=[]
    for kind,expected in [('panel',40),('diagnostics',8)]:
        base=root/'inputs'/kind;man=json.loads((base/'input-manifest.json').read_text());assert len(man['sessions'])==expected
        for item in man['sessions']:
            sid=item['session_id'];assert sid not in seen;seen.add(sid);assert item['path']==sid
            folder=base/item['path'];rows=load(folder/'rows.npz');exact=load(folder/'exact-events.npz');labels=json.loads((folder/'evaluatorlabels.json').read_text());t=rows['t'];units=rows['unit'];clean=rows['clean'];ev=exact['events']
            assert set(rows)=={'t','unit','rms','clean','available_at'}
            assert len(t)%10==0 and np.allclose(t,np.arange(len(t))*.1+.05,rtol=0,atol=1e-10)
            assert np.array_equal(units,np.floor(t)) and np.array_equal(rows['available_at'],units+1)
            assert np.isfinite(clean).all() and clean.shape==(len(t),129) and np.isin(clean,[0,1]).all() and np.all(clean.sum(1)==1)
            assert np.array_equal(rows['rms'],1-clean[:,128]);assert ev.ndim==2 and ev.shape[1]==3
            assert np.isfinite(ev).all() and np.all(ev[:,1]>ev[:,0]) and np.all(ev[1:,0]>=ev[:-1,1]),'strict event order '+sid
            assert np.all(ev[:,2]==np.floor(ev[:,2])) and np.all((ev[:,2]>=0)&(ev[:,2]<128))
            observed=np.full(len(t),128)
            for a,b,p in ev:observed[(t>=a)&(t<b)]=int(p)
            assert np.array_equal(observed,np.argmax(clean,axis=1)),sid
            if 'files' in item:
                for fn,h in item['files'].items():assert sha(folder/fn)==(h['sha256'] if isinstance(h,dict) else h)
            positive=labels['positive'];modes=['full','recent','removed'] if kind=='panel' and positive else ['full']
            for method in ['D','G','G-exact']:
                for mode in modes:planned.append({'kind':kind,'session_id':sid,'method':method,'mode':mode})
            if kind=='panel':
                key=labels['cell'];counts[key]=counts.get(key,0)+1
                if positive:assert labels['truth_stretch']>0 and isinstance(labels['truth_shift'],int)
            entries.append({'kind':kind,'session_id':sid,'observation_hash':canonical(rows),'event_hash':canonical(exact),'rows':len(t),'event_count':len(ev)})
    assert len(planned)==288 and len({tuple(x.values()) for x in planned})==288
    assert all(v==8 for v in counts.values()) and len(counts)==5
    diagnostics=root/'inputs/diagnostics';certificate=json.loads((diagnostics/'ambiguity-certificate.json').read_text());a=load(diagnostics/'collision-world-a/rows.npz');b=load(diagnostics/'collision-world-b/rows.npz');assert canonical(a)==canonical(b)
    ea=load(diagnostics/'collision-world-a/exact-events.npz')['events'];eb=load(diagnostics/'collision-world-b/exact-events.npz')['events'];assert np.array_equal(ea,eb)
    lab_a=json.loads((diagnostics/'collision-world-a/evaluatorlabels.json').read_text());lab_b=json.loads((diagnostics/'collision-world-b/evaluatorlabels.json').read_text());assert lab_a['source_interval']!=lab_b['source_interval']
    # Independent arithmetic proves both complete event correspondences, not a matcher tie.
    target=ea[(ea[:,0]>=10)&(ea[:,1]<=13)]
    witnesses=[]
    for lo,hi,offset in [(0,3,10),(4,7,6)]:
        source=ea[(ea[:,0]>=lo)&(ea[:,1]<=hi)];mapped=source.copy();mapped[:,:2]+=offset
        assert mapped.shape==target.shape and np.allclose(mapped,target,rtol=0,atol=1e-12)
        witnesses.append({'history':[lo,hi],'query':[10,13],'scale':1,'offset':offset,'shift':0,'max_residual':float(np.max(np.abs(mapped-target)))})
    certcheck={'verified':True,'canonical_entire_observation_hash':canonical(a),'exact_events_equal':True,'incompatible_source_intervals':[lab_a['source_interval'],lab_b['source_interval']],'complete_event_witnesses':witnesses,'scope':'Deliberately constructed duplicate-occurrence origin ambiguity, not a witness for any musical-panel family.'}
    (diagnostics/'ambiguity-verification.json').write_text(json.dumps(certcheck,indent=2)+'\n')
    result={'passed':True,'method_hashes':methods,'panel_sessions':40,'diagnostic_sessions':8,'planned_calls':288,'panel_calls':264,'diagnostic_calls':24,'panel_cell_counts':counts,'planned_readouts':planned,'saved_input_checks':entries,'ambiguity_certificate_verified':True,'candidate_calls':0,'generator_calls':0,'runtime_seconds':time.monotonic()-began}
    (root/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    r=validate(pathlib.Path(__file__).resolve().parent);print(json.dumps({k:r[k] for k in ['passed','panel_sessions','planned_calls','runtime_seconds']}))
