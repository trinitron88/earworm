"""Frozen saved-record analysis with common absolute probability coordinates."""
import csv,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from scoring import measure,absolute_distribution,target_distribution,safe
from model import NAMES
HERE=Path(__file__).resolve().parent
CELLS=['matched','timbre','duration','joint']
def dump(path,obj):path.write_text(json.dumps(safe(obj),indent=2,allow_nan=False)+'\n')
def csvwrite(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows([{k:('+Infinity' if v==math.inf else v) for k,v in r.items()} for r in rows])
def main(split):
    out=HERE/'results'/split;out.mkdir(parents=True,exist_ok=True);data=HERE/'data'/split
    truth={x['episode']:x for x in map(json.loads,(data/'truth.jsonl').read_text().splitlines())};cache=list(map(json.loads,(data/'arrived_cache.jsonl').read_text().splitlines()));meta={x['group_id']:x for x in json.loads((HERE/'split_manifest.json').read_text())['groups']}
    rows=[];preds={};obsrows=[]
    for x in cache:
        t=truth[x['episode']];g=t['group_id']
        for name,f in x['forecast']['forecasts'].items():
            preds[(name,g,t['family'],t['condition'],t['variant'])]=f
            rows.append(dict(model=name,group=g,cell=t['family'],condition=t['condition'],variant=t['variant'],**measure(f,t)))
        for i,(o,pitch) in enumerate(zip(x['observations'],t['prefix_true_pitches'])):
            if pitch is None:continue
            for adapter,v in [('old',o),('repaired',o['repaired_observation'])]:
                q=v['pitch_semitones'];err=None if q is None else q-pitch
                obsrows.append(dict(adapter=adapter,group=g,family=meta[g]['family'],register=meta[g]['register'],cell=t['family'],condition=t['condition'],variant=t['variant'],arrival=i,available=float(err is not None),correct=float(err is not None and abs(err)<=.35),absolute_error='' if err is None else abs(err),octave_error=float(err is not None and abs(abs(err)-12)<=.35),two_octave_error=float(err is not None and abs(abs(err)-24)<=.35)))
    csvwrite(out/'trials.csv',rows);csvwrite(out/'observations.csv',obsrows)
    bucket=defaultdict(list)
    for r in rows:bucket[tuple(r[k] for k in ['model','group','cell','condition'])].append(r)
    gr=[]
    for key,rs in bucket.items():
        assert len(rs)==2
        gr.append(dict(zip(['model','group','cell','condition'],key),accuracy=float(np.mean([r['accuracy'] for r in rs])),paired_success=float(all(r['accuracy'] for r in rs)),log_loss=float(np.mean([r['log_loss'] for r in rs])),brier=float(np.mean([r['brier'] for r in rs]))))
    csvwrite(out/'groups.csv',gr)
    groups=sorted({r['group'] for r in rows});rng=np.random.default_rng(2026092020);draw=rng.integers(0,len(groups),(5000,len(groups)))
    def vector(name,cell,condition,metric):
        d={r['group']:r[metric] for r in gr if (r['model'],r['cell'],r['condition'])==(name,cell,condition)};return np.array([d[g] for g in groups])
    def ci(a,q=(.025,.975)):return np.quantile(a[draw].mean(axis=1),q,method='inverted_cdf').tolist()
    summary=[]
    for name,cell,condition in sorted({(r['model'],r['cell'],r['condition']) for r in rows}):
        r=dict(model=name,cell=cell,condition=condition)
        for m in ['accuracy','paired_success','log_loss','brier']:
            a=vector(name,cell,condition,m);lo,hi=ci(a);r.update({m:float(a.mean()),m+'_lower95':lo,m+'_upper95':hi})
        summary.append(r)
    csvwrite(out/'summary.csv',summary)
    obucket=defaultdict(list)
    for r in obsrows:obucket[(r['adapter'],r['group'])].append(r)
    og=[]
    for (adapter,g),rs in obucket.items():
        errors=[r['absolute_error'] for r in rs if r['absolute_error']!=''];og.append(dict(adapter=adapter,group=g,family=meta[g]['family'],register=meta[g]['register'],pitched_blocks=len(rs),availability=float(np.mean([r['available'] for r in rs])),correct=float(np.mean([r['correct'] for r in rs])),mean_absolute_error_available=float(np.mean(errors)) if errors else math.inf,octave_error_rate=float(np.mean([r['octave_error'] for r in rs])),two_octave_error_rate=float(np.mean([r['two_octave_error'] for r in rs]))))
    csvwrite(out/'observation_groups.csv',og)
    osummary=[]
    for adapter in ['old','repaired']:
      for family in ['all','pure','fundamental','overtone']:
        rs=[r for r in og if r['adapter']==adapter and (family=='all' or r['family']==family)]
        summaryrow=dict(adapter=adapter,family=family,groups=len(rs));subdraw=np.random.default_rng(2026092020).integers(0,len(rs),(5000,len(rs)))
        for metric in ['availability','correct','mean_absolute_error_available','octave_error_rate','two_octave_error_rate']:
            vals=np.array([r[metric] for r in rs]);bounds=np.quantile(vals[subdraw].mean(axis=1),[.025,.975],method='inverted_cdf');summaryrow.update({metric:float(vals.mean()),metric+'_lower95':float(bounds[0]),metric+'_upper95':float(bounds[1])})
        osummary.append(summaryrow)
    csvwrite(out/'observation_summary.csv',osummary)
    contrasts=[];controls=[];gates={}
    for name in NAMES:
        good=True;stats={}
        for cond in ['reset','removal']:
            tv=[]
            for g in groups:
                a,b=[np.array(absolute_distribution(preds[(name,g,'joint',cond,v)])) for v in [0,1]];tv.append(float(sum(abs(a-b))/2))
            acc=float(vector(name,'joint',cond,'accuracy').mean());paired=float(vector(name,'joint',cond,'paired_success').mean());ok=acc<=.55 and paired<=.10 and max(tv)<=1e-9;good &=ok;stats[cond]=dict(accuracy=acc,paired_success=paired,max_tv=max(tv),pass_gate=ok)
        diffs=[]
        for g in groups:
            for v in [0,1]:
                a=np.array(absolute_distribution(preds[(name,g,'joint','swap',v)]));b=np.array(absolute_distribution(preds[(name,g,'joint','intact',1-v)]));diffs.append(float(max(abs(a-b))))
        paired=float(vector(name,'joint','swap','paired_success').mean());ok=paired>=.80 and max(diffs)<=1e-9;good &=ok;stats['swap']=dict(paired_success=paired,max_counterpart_difference=max(diffs),pass_gate=ok)
        drop=float((vector(name,'joint','intact','accuracy')-vector(name,'joint','shuffle','accuracy')).mean());ok=drop<=.10;good &=ok;stats['shuffle']=dict(drop=drop,pass_gate=ok)
        amb=[]
        for g in groups:
            for v in [0,1]:
                p=np.array(absolute_distribution(preds[(name,g,'joint','ambiguous',v)]));t=truth[f'{g}/joint/ambiguous/{v}'];y,outside=target_distribution(t);ix=np.flatnonzero(y);mass=float(sum(p[ix]));dev=float(max(abs(p[ix]-.5)));mx=float(max(p));ok=len(ix)==2 and outside==0 and mass>=.90 and dev<=.10 and mx<=.60;amb.append(dict(group=g,variant=v,mass=mass,max_deviation=dev,max_probability=mx,pass_gate=bool(ok)))
        ok=all(r['pass_gate'] for r in amb);good &=ok;stats['ambiguous']=dict(pass_gate=ok,records=amb);controls.append(dict(model=name,pass_gate=bool(good),details=stats))
        familyok=True
        for cell in CELLS[1:]:
            a=vector(name,cell,'intact','accuracy')-vector(name,'matched','intact','accuracy');lo,hi=ci(a,(.05/6,1-.05/6));familyok &=lo>=-.10;contrasts.append(dict(model=name,comparison=cell+'-matched',difference=float(a.mean()),lower_familywise95=lo,upper_familywise95=hi))
        present=name.split('_')[0]+'_present';adv=vector(name,'joint','intact','accuracy')-vector(present,'joint','intact','accuracy');lo,hi=ci(adv)
        cells=all(vector(name,cell,'intact','paired_success').mean()>=.80 for cell in CELLS)
        gates[name]=dict(all_cells_paired_success=bool(cells),joint_over_adapter_present_lower95=lo,simultaneous_noninferiority=bool(familyok),controls=bool(good))
    dump(out/'controls.json',controls);csvwrite(out/'contrasts.csv',contrasts)
    delta=vector('repaired_reference','joint','intact','accuracy')-vector('old_reference','joint','intact','accuracy');lo,hi=ci(delta);comparison=dict(joint_accuracy_gain=float(delta.mean()),lower95=lo,upper95=hi)
    proper=all(vector('repaired_reference','joint','intact',m).mean()<=vector('old_reference','joint','intact',m).mean() for m in ['log_loss','brier'])
    guardgroups=[g for g in groups if meta[g]['family'] in ['pure','fundamental']];guards=[r for r in og if r['adapter']=='repaired' and r['group'] in guardgroups];correct=float(np.mean([r['correct'] for r in guards]));octave=float(np.mean([r['octave_error_rate'] for r in guards]));indices=[groups.index(g) for g in guardgroups];loss=float(np.mean([(vector('old_reference',cell,'intact','accuracy')-vector('repaired_reference',cell,'intact','accuracy'))[indices].mean() for cell in CELLS]));safety=correct>=.95 and octave<=.01 and loss<=.05
    guard=dict(groups=guardgroups,pitch_correct=correct,octave_error_rate=octave,prediction_accuracy_loss=loss,pass_gate=bool(safety));dump(out/'octave_safety.json',guard)
    g=gates['repaired_reference'];valid=json.loads((HERE/'validation'/f'{split}.json').read_text())['all_pass']
    adoption=valid and g['all_cells_paired_success'] and g['joint_over_adapter_present_lower95']>0 and g['simultaneous_noninferiority'] and g['controls'] and delta.mean()>=.10 and lo>0 and proper and safety
    branch='A' if adoption else ('B' if valid else 'invalid')
    decision=dict(branch=branch,validity_passed=valid,comparison=comparison,proper_scores_no_worse=bool(proper),octave_safety=guard,model_gates=gates,next_action='After exact-head review, PM may assign isolated-voice boundary test with repaired version.' if branch=='A' else 'Do not adopt; after review PM chooses a different bounded prerequisite approach. No second run here.')
    dump(out/'decision.json',decision);print(json.dumps(safe(decision)))
if __name__=='__main__':
    import sys;main(sys.argv[1])
