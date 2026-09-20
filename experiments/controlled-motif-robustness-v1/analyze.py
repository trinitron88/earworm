"""Saved-record evaluator. Oracle is evaluator-only and never sent to worker."""
import json,math,csv,copy
from pathlib import Path
from collections import defaultdict
import numpy as np
from model import forecast,NAMES
HERE=Path(__file__).resolve().parent
CELLS=['matched','timbre','duration','joint']
def writecsv(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def target(t,anchor):
    y=np.zeros(50);errors=[]
    for v,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):
        off=None if anchor is None else t['prefix_true_pitches'][-1]+v-anchor
        k=49 if off is None or not -24.5<off<24.5 else int(round(off))+24
        y[k]+=mass
        if k!=49:errors.append(abs(off-round(off)))
    return y,max(errors,default=0.)
def measure(f,t):
    p=np.array(f['probabilities']);assert np.isfinite(p).all() and min(p)>=0 and abs(p.sum()-1)<1e-12
    y,quant=target(t,f['anchor_semitones'])
    ll=sum(-y[k]*math.log(p[k]) if p[k]>0 else math.inf for k in np.flatnonzero(y))
    point=f['point_pitch_semitones']
    return dict(accuracy=float(point is not None and abs(point-t['pitch_semitones'])<=.35),log_loss=ll,brier=float(sum((p-y)**2)+1-sum(y*y)),target_quantization_error=quant)
def main(split):
    out=HERE/'results'/split;out.mkdir(parents=True,exist_ok=True)
    data=HERE/'data'/split
    truth={x['episode']:x for x in map(json.loads,(data/'truth.jsonl').read_text().splitlines())}
    cfg=json.loads((data/'config_used.json').read_text())
    cache=list(map(json.loads,(data/'arrived_cache.jsonl').read_text().splitlines()))
    rows=[];preds={};oracle_records=[]
    for x in cache:
        t=truth[x['episode']]
        # This routine runs only after whole acoustic split is complete.
        assert (data/'runtime.json').exists()
        history=[]
        for i,(obs,pitch) in enumerate(zip(x['observations'],t['prefix_true_pitches'])):
            if t['reset_before_index']==i:history=[]
            obs=copy.deepcopy(obs);obs['pitch_semitones']=pitch;obs['pitch_available']=pitch is not None
            obs['pitch_hz']=None if pitch is None else 220*2**(pitch/12)
            history.append(obs)
        oracle=forecast(history,cfg)
        oracle_records.append(dict(episode=t['episode'],diagnostic_only=True,arrived_fundamentals=t['prefix_true_pitches'],forecasts=oracle))
        for kind,outputs in [('acoustic',x['forecast']['forecasts']),('oracle',oracle)]:
            for name,f in outputs.items():
                key=(kind,name,t['group_id'],t['family'],t['condition'],t['variant']);preds[key]=f
                rows.append(dict(kind=kind,model=name,group=t['group_id'],cell=t['family'],condition=t['condition'],variant=t['variant'],**measure(f,t)))
    (out/'oracle_diagnostic.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in oracle_records))
    writecsv(out/'trials.csv',rows)
    buckets=defaultdict(list)
    for r in rows:buckets[tuple(r[k] for k in ['kind','model','group','cell','condition'])].append(r)
    gr=[]
    for key,rs in buckets.items():
        assert len(rs)==2
        gr.append(dict(zip(['kind','model','group','cell','condition'],key),accuracy=np.mean([r['accuracy'] for r in rs]),paired_success=float(all(r['accuracy'] for r in rs)),log_loss=np.mean([r['log_loss'] for r in rs]),brier=np.mean([r['brier'] for r in rs]),target_quantization_error=max(r['target_quantization_error'] for r in rs)))
    writecsv(out/'groups.csv',gr)
    groups=sorted({r['group'] for r in gr});rng=np.random.default_rng(2026092007);draw=rng.integers(0,len(groups),(5000,len(groups)))
    def vector(kind,name,cell,condition,metric):
        d={r['group']:r[metric] for r in gr if (r['kind'],r['model'],r['cell'],r['condition'])==(kind,name,cell,condition)}
        return np.array([d[g] for g in groups])
    def ci(a,q=(.025,.975)):return np.quantile(a[draw].mean(axis=1),q).tolist()
    summary=[]
    for kind,name,cell,condition in sorted({(r['kind'],r['model'],r['cell'],r['condition']) for r in gr}):
        r=dict(kind=kind,model=name,cell=cell,condition=condition)
        for metric in ['accuracy','paired_success','log_loss','brier']:
            a=vector(kind,name,cell,condition,metric);lo,hi=ci(a);r.update({metric:float(a.mean()),metric+'_lower95':lo,metric+'_upper95':hi})
        summary.append(r)
    writecsv(out/'summary.csv',summary)
    controls=[];contrasts=[];passes={}
    for kind in ['acoustic','oracle']:
      for name in NAMES:
        stats={};good=True
        for condition in ['reset','removal']:
            tv=[]
            for g in groups:
                a,b=[np.array(preds[(kind,name,g,'joint',condition,v)]['probabilities']) for v in [0,1]];tv.append(float(sum(abs(a-b))/2))
            acc=float(vector(kind,name,'joint',condition,'accuracy').mean());paired=float(vector(kind,name,'joint',condition,'paired_success').mean())
            ok=acc<=.55 and paired<=.10 and max(tv)<=1e-9;good &= ok
            stats[condition]=dict(accuracy=acc,paired_success=paired,max_pair_total_variation=max(tv),pass_gate=ok)
        diffs=[]
        for g in groups:
            for v in [0,1]:
                a=np.array(preds[(kind,name,g,'joint','swap',v)]['probabilities']);b=np.array(preds[(kind,name,g,'joint','intact',1-v)]['probabilities']);diffs.append(float(max(abs(a-b))))
        paired=float(vector(kind,name,'joint','swap','paired_success').mean());ok=paired>=.80 and max(diffs)<=1e-9;good &=ok
        stats['swap']=dict(paired_success=paired,max_counterpart_difference=max(diffs),pass_gate=ok)
        drop=float((vector(kind,name,'joint','intact','accuracy')-vector(kind,name,'joint','shuffle','accuracy')).mean());ok=drop<=.10;good &=ok;stats['shuffle']=dict(accuracy_drop=drop,pass_gate=ok)
        ambiguity=[]
        for g in groups:
            for v in [0,1]:
                f=preds[(kind,name,g,'joint','ambiguous',v)];t=truth[f'{g}/joint/ambiguous/{v}'];y,_=target(t,f['anchor_semitones']);ix=np.flatnonzero(y);p=np.array(f['probabilities']);mass=float(sum(p[ix]));dev=max(abs(p[ix]-.5));maxp=float(max(p));ok=len(ix)==2 and mass>=.90 and dev<=.10 and maxp<=.60
                ambiguity.append(dict(group=g,variant=v,mass=mass,max_deviation=float(dev),max_probability=maxp,pass_gate=bool(ok)))
        ok=all(x['pass_gate'] for x in ambiguity);good &=ok;stats['ambiguous']=dict(pass_gate=ok,records=ambiguity)
        controls.append(dict(kind=kind,model=name,pass_gate=bool(good),details=stats))
        cells_ok=all(vector(kind,name,c,'intact','paired_success').mean()>=.80 for c in CELLS)
        delta=vector(kind,name,'joint','intact','accuracy')-vector(kind,'present','joint','intact','accuracy');lo,hi=ci(delta)
        proper=all(vector(kind,name,'joint','intact',m).mean()<=vector(kind,'present','joint','intact',m).mean()+1e-12 for m in ['log_loss','brier'])
        family_ok=True
        for cell in CELLS[1:]:
            diff=vector(kind,name,cell,'intact','accuracy')-vector(kind,name,'matched','intact','accuracy');fl,fh=ci(diff,(.05/6,1-.05/6));family_ok &= fl>=-.10
            contrasts.append(dict(kind=kind,model=name,comparison=cell+'-matched',difference=float(diff.mean()),lower_familywise95=fl,upper_familywise95=fh))
        passes[kind+'/'+name]=dict(pass_gate=bool(cells_ok and lo>0 and proper and family_ok and good),all_cell_paired_success=cells_ok,joint_over_present_lower95=lo,proper_scores=bool(proper),simultaneous_noninferiority=bool(family_ok),controls=bool(good))
    writecsv(out/'contrasts.csv',contrasts)
    (out/'controls.json').write_text(json.dumps(controls,indent=2))
    comparisons=[]
    for left,right in [('acoustic/candidate','acoustic/reference'),('oracle/candidate','acoustic/candidate'),('oracle/reference','acoustic/reference')]:
        ak,am=left.split('/');bk,bm=right.split('/');diff=vector(ak,am,'joint','intact','accuracy')-vector(bk,bm,'joint','intact','accuracy');lo,hi=ci(diff)
        comparisons.append(dict(left=left,right=right,difference=float(diff.mean()),lower95=lo,upper95=hi))
    writecsv(out/'paired_comparisons.csv',comparisons)
    ref=passes['acoustic/reference']['pass_gate'];cand=passes['acoustic/candidate']['pass_gate'];delta=comparisons[0]
    proper=all(vector('acoustic','candidate','joint','intact',m).mean()<=vector('acoustic','reference','joint','intact',m).mean()+1e-12 for m in ['log_loss','brier'])
    if ref:branch='A'
    elif cand and delta['difference']>=.10 and delta['lower95']>0 and proper:branch='B'
    elif not ref and not cand and passes['oracle/candidate']['pass_gate'] and comparisons[1]['difference']>=.10 and comparisons[1]['lower95']>0:branch='C'
    else:branch='inconclusive'
    validation=json.loads((HERE/'validation'/f'{split}.json').read_text())
    if not validation['all_pass']:branch='invalid'
    decision=dict(branch=branch,validity_passed=validation['all_pass'],gates=passes,comparisons=comparisons,oracle='Evaluator-only non-acoustic diagnostic, not a deployed capability.',next_action={'A':'After review, propose bounded continuous isolated-voice boundary test with original reference.','B':'After review, propose boundary test with selected reparameterization.','C':'Withhold robustness claim; after review, PM may assign one observation repair with fresh confirmatory groups. No new run authorized here.','inconclusive':'PM must present Brian one concrete prerequisite choice; do not automatically audit.','invalid':'Preserve failed validity and stop; no capability branch.'}[branch])
    (out/'decision.json').write_text(json.dumps(decision,indent=2));print(json.dumps(decision))
if __name__=='__main__':
    import sys;main(sys.argv[1])
