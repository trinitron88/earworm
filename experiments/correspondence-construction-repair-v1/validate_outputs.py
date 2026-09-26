"""Independent saved-output inspection: no matcher imports or executions."""
from __future__ import annotations
import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
from score import expected_readouts

def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def arrays(path):
    with np.load(path, allow_pickle=False) as z: return {k:z[k] for k in z.files}
def near(a,b): return abs(float(a)-float(b)) <= 1e-8 * (1+abs(float(a))+abs(float(b)))
def need(condition, message):
    if not condition: raise ValueError(message)
def pitch_at(events,t):
    hit=events[(events[:,0] <= t) & (t < events[:,1])]
    return int(hit[0,2]) if len(hit) else 128

def global_witness(candidate, state, events, exact):
    t, units = state['t'], state['unit']; labels=np.argmax(state['clean'],axis=1)
    last=np.flatnonzero(state['rms']>1e-4)[-1]
    qi=np.flatnonzero((t>t[last]-2+1e-8)&(t<=t[last]+1e-8))
    hi=np.flatnonzero(units<units[qi[0]])
    a=float(candidate['scale']); b=float(candidate['offset']); shift=int(candidate['shift'])
    need(.65-1e-12<=a<=1.5+1e-12 and -5<=shift<=5,'G transformation outside fixed bounds')
    need(candidate['verified_query_rows']==qi.tolist(),'G did not verify every available query row')
    need(candidate['query_rows_skipped']==0 and candidate['contradictions']==0,'G coverage/contradiction claim invalid')
    need(near(candidate['start'],(t[qi[0]]-b)/a) and near(candidate['end'],(t[qi[-1]]-b)/a),'G inverse support mismatch')
    hs=candidate['history_support']; component=hi[(t[hi]>=hs[0]-1e-9)&(t[hi]<=hs[1]+1e-9)]
    need(len(component)>=2 and near(t[component[0]],hs[0]) and near(t[component[-1]],hs[1]),'G unsupported history component')
    need(np.all(np.diff(t[component])<=.10001),'G bridges missing history support')
    need(candidate['start']>=hs[0]-1e-8 and candidate['end']<=hs[1]+1e-8,'G leaves retained support')
    qs=[int(x['query_pitch']) for x in candidate['correspondence']]
    need(all((x['query_pitch']==128 and x['history_pitch']==128) or
             (x['query_pitch']!=128 and x['history_pitch']!=128 and x['query_pitch']==x['history_pitch']+shift)
             for x in candidate['correspondence']),'G correspondence pitch inconsistency')
    boundaries=candidate['boundary_witnesses']; qb=np.array([x['query_boundary'] for x in boundaries])
    need(len(qs)==len(qb)+1 and np.all(np.diff(qb)>0),'G unordered boundary witness')
    for x in boundaries:
        need(near(x['query_boundary'],a*x['history_boundary']+b),'G boundary transform mismatch')
        for which in ('query','history'):
            lo,up,opened=x[which+'_bracket']; value=x[which+'_boundary']
            need(value>=lo-1e-8 and value<=up+1e-8 and (not opened or value>lo),'G boundary outside sampling bracket')
    need(np.array_equal(np.asarray(qs)[np.searchsorted(qb,t[qi],side='right')],labels[qi]),'G query row contradiction')
    origin=candidate['constraint_coordinate_origins']; local=candidate['local_representative']
    # Preserve the declared local coordinate arithmetic: re-expanding a global
    # offset can move an exact boundary by a floating-point rounding unit.
    mapped=a*(t[component]-origin['history'])+local[1]+origin['query']
    inside=(mapped>=t[qi[0]])&(mapped<=t[qi[-1]])
    ids=component[inside]; shifted=np.where(labels[ids]==128,128,labels[ids]+shift)
    need(np.array_equal(np.asarray(qs)[np.searchsorted(qb,mapped[inside],side='right')],shifted),'G history row contradiction')
    need(candidate['verified_history_rows']==ids.tolist(),'G history coverage mismatch')
    need(near(local[0],a) and near(origin['query']+local[1]-a*origin['history'],b),'G local/global coordinates mismatch')
    for c in candidate['constraints']:
        lhs=c['scale_coefficient']*local[0]+c['offset_coefficient']*local[1]
        need(lhs<=c['upper_bound']+1e-8 and (not c['strict'] or lhs<c['upper_bound']),'G violated serialized inequality')
    poly=candidate['feasible_polygon']; need(bool(poly),'G lacks feasible polygon')
    for aa,bb in poly:
        need(.65-1e-8<=aa<=1.5+1e-8,'G polygon outside scale box')
        lb=bb-origin['query']+aa*origin['history']
        for c in candidate['constraints']:
            need(c['scale_coefficient']*aa+c['offset_coefficient']*lb<=c['upper_bound']+1e-7,'G polygon violates closure inequality')
    need(near(min(x[0] for x in poly),candidate['scale_range'][0]) and near(max(x[0] for x in poly),candidate['scale_range'][1]),'G scale range mismatch')
    if exact:
        # Independently check every continuous interval induced by exact note edges.
        qlo,qhi=t[qi[0]],t[qi[-1]]; edges={float(qlo),float(qhi)}
        for on,off,_ in events:
            for edge in (on,off,a*on+b,a*off+b):
                if qlo<edge<qhi: edges.add(float(edge))
        ordered=sorted(edges); probes=[(x+y)/2 for x,y in zip(ordered,ordered[1:]) if y-x>1e-9]
        for qt in probes:
            hp=pitch_at(events,(qt-b)/a); qp=pitch_at(events,qt)
            need(qp==(128 if hp==128 else hp+shift),'G-exact continuous support contradiction')
    return {'query_rows':len(qi),'history_rows':len(ids),'candidate_witness_checked':True}

def d_witness(answer,state):
    raw=answer['raw_historical']; h=raw.get('hypothesis')
    need(bool(answer['accepted'])==(h is not None and raw['distance']<=0),'D acceptance differs from threshold0')
    if h is None:return
    t=state['t'];labels=np.argmax(state['clean'],axis=1);loud=np.flatnonzero(state['rms']>1e-4)
    qi=np.flatnonzero((t>t[loud[-1]]-2+1e-8)&(t<=t[loud[-1]]+1e-8))
    path=h['path'];need(path and path[0][0]==qi[0] and path[-1][0]==qi[-1],'D endpoint coverage')
    shift=h['shift'];bad=0
    for q,j in path:
        need(q in qi and state['unit'][j]<state['unit'][qi[0]],'D invalid/future path index')
        bad+=not ((labels[q]==labels[j]==128) or (labels[q]!=128 and labels[j]!=128 and labels[q]==labels[j]+shift))
    for (q,j),(r,k) in zip(path,path[1:]):
        need((r-q,k-j) in ((1,1),(1,2),(2,1)),'D invalid path step')
    hist=np.arange(path[0][1],path[-1][1]+1)
    need(np.all(np.diff(t[hist])<=.10001),'D crosses history removal hole')
    need(near(raw['distance'],bad/len(qi)),'D saved cost does not equal anchor costs / query length')
    ratio=len(qi)*.1/(t[path[-1][1]]-t[path[0][1]]+.1)
    need(near(h['stretch'],ratio) and .65<=ratio<=1.5,'D span-ratio mismatch')

def validate(root):
    root=Path(root); errors=[]; checks=[]; started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def problem(where,e): errors.append({'path':str(where),'error':type(e).__name__+': '+str(e)})
    freeze=root/'freeze.json'
    try:
        for rel,value in read(freeze)['files'].items():
            expected=value['sha256'] if isinstance(value,dict) else value
            need(sha(root/rel)==expected,'Frozen file changed: '+rel)
    except Exception as e:problem('freeze.json',e)
    try:
        old=root.parent/'correspondence-reference-choice-v1'
        for rel in ('engine.py','global_matcher.py','historical/matching.py','historical/listener.py'):
            need(sha(root/rel)==sha(old/rel),'Frozen PR19 method changed: '+rel)
        for name,expected in read(root/'baseline-hashes.json').items():
            need(sha(root/'historical'/name)==expected,'Historical baseline hash mismatch: '+name)
    except Exception as e:problem('unchanged-methods',e)
    counts={'panel':0,'diagnostics':0}; retained_checks=[]
    for suite in ('panel','diagnostics'):
        try: entries=list(expected_readouts(root,suite))
        except Exception as e:problem('inputs/'+suite,e);continue
        need_count=264 if suite=='panel' else 24
        if len(entries)!=need_count:problem(suite,ValueError('Wrong expected readout count'))
        for sid,folder,labels,method,mode,out in entries:
            try:
                for name in ('started.json','response.json','arrivals.json','completed.json'):
                    need((out/name).is_file(),'Missing '+name)
                answer=read(out/'response.json'); complete=read(out/'completed.json'); arrivals=read(out/'arrivals.json')
                need(complete['returncode']==0,'Child software failure')
                need(answer['method']==method and answer['mode']==mode,'Method/control output mismatch')
                need(answer['actual_output_availability_upper_bound']>=answer['prediction_finished_monotonic'],'Output availability precedes prediction')
                need(near(answer['actual_output_availability_upper_bound'],answer['parent_response_received_monotonic']),'Availability receipt differs')
                need(answer['readout_roundtrip_seconds']>=0 and answer['compute_seconds']>=0,'Negative computation interval')
                rows=arrays(folder/'rows.npz'); original_units=sorted(set(map(int,rows['unit'])))
                need(len(arrivals)==len(original_units),'Missing arrival receipts')
                need([x['unit'] for x in arrivals]==original_units,'Arrival unit order')
                need(all(x['simulated_available_at']==x['unit']+1 for x in arrivals),'Early arrival availability')
                source=labels.get('source_interval'); removed=[u for u in original_units if source and u<source[1] and u+1>source[0]] if mode=='removed' else []
                expected=original_units[-4:] if mode=='recent' else original_units[-60:]
                expected=[u for u in expected if u not in removed]
                need(answer['kept_units']==expected and answer['removed_units']==removed,'Incomplete destructive control')
                keep=np.isin(rows['unit'],expected); state={k:v[keep] for k,v in rows.items()}
                need(hashlib.sha256(state['clean'].tobytes()).hexdigest()==answer['retained_observation_sha256'],'Retained observations changed')
                need(hashlib.sha256(state['t'].tobytes()).hexdigest()==answer['retained_timestamps_sha256'],'Retained timestamps changed')
                need(answer['predictor_accessible_state_bytes']<=8*1024**2 and answer['retained_peak_bytes']<=8*1024**2,'Persistent storage cap')
                need(answer['persistent_replacements']==max(0,len(original_units)-60),'Replacement count mismatch')
                if mode=='removed' and answer['accepted']:
                    h=answer['selected'];center=(h['start']+h['end'])/2
                    need(not source[0]<=center<source[1],'Claims removed source identity')
                if method=='D': d_witness(answer,state)
                else:
                    candidates=answer.get('candidates',[])
                    need(answer['candidate_count']==len(candidates),'Candidate count mismatch')
                    need(bool(answer['accepted'])==(len(candidates)==1),'G deterministic abstention rule mismatch')
                    events=arrays(folder/'exact-events.npz')['events'] if method=='G-exact' else None
                    for c in candidates:global_witness(c,state,events,method=='G-exact')
                    if answer['accepted']:need(answer['selected']==candidates[0],'G selected wrong candidate')
                counts[suite]+=1
                checks.append({'suite':suite,'session_id':sid,'method':method,'mode':mode,'passed':True})
            except Exception as e:problem(out.relative_to(root),e)
    budget={}
    try:
        budget=read(root/'resources.json')
        for key,cap in [('cumulative_calls',400),('cumulative_compute_seconds',7200),('additional_compute_seconds',3400),('new_artifact_bytes',512*1024**2),('spend',0)]:
            need(key in budget and 0<=budget[key]<=cap,'Resource cap/evidence: '+key)
        need(budget['cumulative_calls']>=32+288,'Resource call ledger undercounts reserved qualification and completed readouts')
    except Exception as e:problem('resources.json',e)
    certificate_verified=False
    try:
        certpath=root/'inputs/diagnostics/ambiguity-certificate.json'
        if certpath.exists():
            cert=read(certpath)
            receipt=read(certpath.with_name('ambiguity-verification.json'))
            need(receipt.get('verified') is True,'Missing independent ambiguity-verification receipt')
            worlds=cert['worlds'];need(len(worlds)==2,'Certificate requires two worlds')
            base=certpath.parent
            aa=arrays(base/worlds[0]/'rows.npz');bb=arrays(base/worlds[1]/'rows.npz')
            need(set(aa)==set(bb),'World input schemas differ')
            for k in aa:
                need(aa[k].dtype==bb[k].dtype and np.array_equal(aa[k],bb[k]),'World observations differ: '+k)
            ea=arrays(base/worlds[0]/'exact-events.npz')['events'];eb=arrays(base/worlds[1]/'exact-events.npz')['events']
            need(np.array_equal(ea,eb),'World exact events differ')
            la=read(base/worlds[0]/'evaluatorlabels.json');lb=read(base/worlds[1]/'evaluatorlabels.json')
            need(la['source_interval']!=lb['source_interval'],'World labels are compatible')
            for w in cert['explicit_correspondences']:
                lo,hi=w['history_interval'];ql,qh=w['query_interval']
                source=ea[(ea[:,0]>=lo)&(ea[:,1]<=hi)].copy()
                target=ea[(ea[:,0]>=ql)&(ea[:,1]<=qh)]
                source[:,:2]=source[:,:2]*w['scale']+w['offset'];source[:,2]+=w['shift']
                need(len(source)>0 and source.shape==target.shape and np.allclose(source,target,atol=1e-12,rtol=0),'Whole-event ambiguity witness invalid')
            certificate_verified=counts['diagnostics']==24
    except Exception as e:problem('ambiguity-certificate.json',e)
    return {'schema':'correspondence-independent-saved-output-validation-v1','started_utc':started,
            'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'passed':not errors and counts=={'panel':264,'diagnostics':24},'completed_readouts':counts,
            'errors':errors,'checks':checks,'resource_evidence':budget,
            'ambiguity_certificate_verified':certificate_verified,
            'ambiguity_check_scope':'Separate independent construction-checker certificate; no inference from candidate scores.',
            'new_candidate_calls':0,'new_material_generations':0,
            'verification_scope':'Saved arrival/removal/hash/budget/arithmetic/witness checks; no dynamic matcher completeness proof.'}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',nargs='?',default=Path(__file__).parent);a=p.parse_args()
    result=validate(a.root);(Path(a.root)/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'passed':result['passed'],'completed_readouts':result['completed_readouts'],'errors':result['errors']}))
