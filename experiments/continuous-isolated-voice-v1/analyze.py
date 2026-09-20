"""Frozen saved-event evaluation; oracle boundaries never enter operational API."""
import json,csv,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from scoring import measure,absolute_distribution,target_distribution,safe
from events import event_metrics
from model import NAMES
HERE=Path(__file__).resolve().parent;CELLS=['detached','legato','duration','joint']
def dump(path,obj):path.write_text(json.dumps(safe(obj),indent=2,allow_nan=False)+'\n')
def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows([{k:safe(v) for k,v in r.items()} for r in rows])
def main(split):
    d=HERE/'data'/split;out=HERE/'results'/split;out.mkdir(parents=True,exist_ok=True);cfg=json.loads((d/'config_used.json').read_text());selected=cfg['selected'];truth={r['episode']:r for r in map(json.loads,(d/'truth.jsonl').read_text().splitlines())};cache=list(map(json.loads,(d/'cache.jsonl').read_text().splitlines()));rows=[];erows=[];preds={};diagnostic=[]
    for x in cache:
        t=truth[x['episode']];outputs={'streaming':x['operational']['forecasts'][selected],'fixed':x['operational']['forecasts']['fixed'],'oracle-boundary':x['oracle_forecasts']};evs={'streaming':x['operational']['events'][selected],'fixed':x['operational']['events']['fixed'],'oracle-boundary':x['oracle_events']}
        for front,fs in outputs.items():
            for name,f in fs.items():
                model=front+'/'+name;preds[(model,t['group'],t['cell'],t['condition'],t['variant'])]=f;rows.append(dict(model=model,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**measure(f,t)))
            m=event_metrics(evs[front],t['bounds'],t['reset_sample']);erows.append(dict(front=front,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**{k:v for k,v in m.items() if k!='matches'}))
            if front=='streaming':
                true=[b for b in t['bounds'] if b['pitch'] is not None and (t['reset_sample'] is None or b['start']>=t['reset_sample'])];pp=[e for e in evs[front] if e.get('state_pitch',e['observation']['pitch_semitones']) is not None]
                for match in m['matches']:
                    a,b=pp[match['predicted']],true[match['truth']];q=a['observation']['pitch_semitones'];wrong=q is None or abs(q-b['pitch'])>.35
                    if wrong:diagnostic.append(dict(episode=x['episode'],true_start=b['start'],true_end=b['end'],inferred_start=a['start_sample'],inferred_end=a['end_sample'],true_pitch=b['pitch'],estimated_pitch=q,bound_difference=a['start_sample']!=b['start'] or a['end_sample']!=b['end']))
    table(out/'trials.csv',rows);table(out/'event_trials.csv',erows);dump(out/'boundary_window_diagnostic.json',diagnostic)
    groups=sorted({r['group'] for r in rows});models=sorted({r['model'] for r in rows});draw=np.random.default_rng(2026092030).integers(0,len(groups),(5000,len(groups)))
    def ci(a,q=(.025,.975)):return np.quantile(np.asarray(a)[draw].mean(axis=1),q,method='inverted_cdf').tolist()
    bucket=defaultdict(list)
    for r in rows:bucket[tuple(r[k] for k in ['model','group','cell','condition'])].append(r)
    gr=[]
    for key,rs in bucket.items():
        assert len(rs)==2;gr.append(dict(zip(['model','group','cell','condition'],key),accuracy=float(np.mean([r['accuracy'] for r in rs])),paired_success=float(all(r['accuracy'] for r in rs)),log_loss=float(np.mean([r['log_loss'] for r in rs])),brier=float(np.mean([r['brier'] for r in rs]))))
    table(out/'groups.csv',gr)
    def vector(model,cell,cond,metric):
        m={r['group']:r[metric] for r in gr if (r['model'],r['cell'],r['condition'])==(model,cell,cond)};return np.array([m[g] for g in groups])
    summary=[]
    for model,cell,cond in sorted({(r['model'],r['cell'],r['condition']) for r in rows}):
        r=dict(model=model,cell=cell,condition=cond)
        for metric in ['accuracy','paired_success','log_loss','brier']:
            vals=vector(model,cell,cond,metric);lo,hi=ci(vals);r.update({metric:float(vals.mean()),metric+'_lower95':lo,metric+'_upper95':hi})
        summary.append(r)
    table(out/'summary.csv',summary)
    eg=[];eventmetrics=['precision','recall','f1','split_rate','merge_rate','pitch_accuracy','pitch_availability','octave_error_rate','mean_pitch_error_available','mean_onset_error_s','mean_end_error_s']
    for front in ['streaming','fixed','oracle-boundary']:
      for g in groups:
        rs=[r for r in erows if r['front']==front and r['group']==g];v=dict(front=front,group=g)
        for metric in eventmetrics:
            vals=[r[metric] for r in rs if r[metric] is not None];v[metric]=float(np.mean(vals)) if vals else None
        v['max_true_end_latency_s']=max(r['max_true_end_latency_s'] for r in rs);v['max_inferred_end_latency_s']=max(r['max_inferred_end_latency_s'] for r in rs);eg.append(v)
    table(out/'event_groups.csv',eg);es=[]
    for front in ['streaming','fixed','oracle-boundary']:
        rs=[r for r in eg if r['front']==front];v={'front':front}
        for metric in eventmetrics:
            vals=np.array([r[metric] if r[metric] is not None else math.inf for r in rs]);lo,hi=ci(vals);v.update({metric:float(vals.mean()),metric+'_lower95':lo,metric+'_upper95':hi})
        v['max_true_end_latency_s']=max(r['max_true_end_latency_s'] for r in rs);v['max_inferred_end_latency_s']=max(r['max_inferred_end_latency_s'] for r in rs);es.append(v)
    table(out/'event_summary.csv',es)
    controls=[];controlpass={}
    for model in models:
        good=True;stats={}
        for cond in ['reset','removal']:
            tv=[]
            for g in groups:
                a,b=[np.array(absolute_distribution(preds[(model,g,'joint',cond,v)])) for v in [0,1]];tv.append(float(sum(abs(a-b))/2))
            acc=float(vector(model,'joint',cond,'accuracy').mean());paired=float(vector(model,'joint',cond,'paired_success').mean());ok=acc<=.55 and paired<=.10 and max(tv)<=1e-9;good &=ok;stats[cond]=dict(accuracy=acc,paired_success=paired,max_tv=max(tv),pass_gate=ok)
        differences=[]
        for g in groups:
            for v in [0,1]:
                a=np.array(absolute_distribution(preds[(model,g,'joint','swap',v)]));b=np.array(absolute_distribution(preds[(model,g,'joint','intact',1-v)]));differences.append(float(max(abs(a-b))))
        paired=float(vector(model,'joint','swap','paired_success').mean());ok=paired>=.8 and max(differences)<=1e-9;good &=ok;stats['swap']=dict(paired_success=paired,max_counterpart_difference=max(differences),pass_gate=ok)
        drop=float((vector(model,'joint','intact','accuracy')-vector(model,'joint','shuffle','accuracy')).mean());ok=drop<=.1;good &=ok;stats['shuffle']=dict(drop=drop,pass_gate=ok)
        ar=[]
        for g in groups:
            for v in [0,1]:
                p=np.array(absolute_distribution(preds[(model,g,'joint','ambiguous',v)]));t=truth[f'{g}/joint/ambiguous/{v}'];y,outer=target_distribution(t);ix=np.flatnonzero(y);mass=float(sum(p[ix]));dev=float(max(abs(p[ix]-.5)));mx=float(max(p));ok=outer==0 and mass>=.9 and dev<=.1 and mx<=.6;ar.append(dict(group=g,variant=v,mass=mass,max_deviation=dev,max_probability=mx,pass_gate=bool(ok)))
        ok=all(x['pass_gate'] for x in ar);good &=ok;stats['ambiguous']=dict(pass_gate=ok,records=ar);controls.append(dict(model=model,pass_gate=bool(good),details=stats));controlpass[model]=bool(good)
    dump(out/'controls.json',controls)
    contrasts=[];noninferior=True
    for model in NAMES:
      for cell in CELLS:
        vals=vector('streaming/'+model,cell,'intact','accuracy')-vector('oracle-boundary/'+model,cell,'intact','accuracy');lo,hi=ci(vals,(.05/8,1-.05/8));contrasts.append(dict(model=model,cell=cell,streaming_minus_oracle=float(vals.mean()),lower_familywise95=lo,upper_familywise95=hi))
        if model=='reference':noninferior &=lo>=-.1
    table(out/'comparisons.csv',contrasts)
    primary='streaming/reference';ceiling='oracle-boundary/reference';oracle_pass=all(vector(ceiling,c,'intact','paired_success').mean()>=.8 for c in CELLS);stream_pass=all(vector(primary,c,'intact','paired_success').mean()>=.8 for c in CELLS)
    advantage=vector(primary,'joint','intact','accuracy')-vector('streaming/present','joint','intact','accuracy');lo,hi=ci(advantage)
    increases={m:float(vector(primary,'joint','intact',m).mean()-vector(ceiling,'joint','intact',m).mean()) for m in ['log_loss','brier']}
    ev=next(r for r in es if r['front']=='streaming');ov=next(r for r in es if r['front']=='oracle-boundary');event_pass=ev['f1']>=.90 and ev['pitch_accuracy']>=.95 and ev['split_rate']<=.05 and ev['merge_rate']<=.05;latency=ev['max_true_end_latency_s']<=.160 and ev['max_inferred_end_latency_s']<=.160
    meta={g['group_id']:g for g in json.loads((HERE/'split_manifest.json').read_text())['groups']};safety=[]
    for family in ['pure','fundamental','overtone']:
        ix=[i for i,g in enumerate(groups) if meta[g]['family']==family];loss=float(np.mean([(vector(ceiling,c,'intact','accuracy')-vector(primary,c,'intact','accuracy'))[ix].mean() for c in CELLS]));safety.append(dict(family=family,groups=len(ix),accuracy_loss_vs_oracle=loss,pass_gate=loss<=.10))
    safety_pass=all(x['pass_gate'] for x in safety) and ev['octave_error_rate']<=.01;dump(out/'safety.json',dict(families=safety,octave_error_rate=ev['octave_error_rate'],pass_gate=bool(safety_pass)))
    wrong_fraction=sum(x['bound_difference'] for x in diagnostic)/len(diagnostic) if diagnostic else 0.
    localized=ev['f1']<.9 or ev['split_rate']>.05 or ev['merge_rate']>.05 or (ov['pitch_accuracy']>=.95 and ev['pitch_accuracy']<.95 and wrong_fraction>=.9)
    valid=json.loads((HERE/'validation'/f'{split}.json').read_text())['all_pass'];adopt=oracle_pass and stream_pass and noninferior and lo>0 and increases['log_loss']<=.10 and increases['brier']<=.02 and event_pass and latency and controlpass[primary] and safety_pass
    branch='invalid' if not valid else ('C' if not oracle_pass else ('A' if adopt else ('B' if localized else 'inconclusive')))
    decision=dict(branch=branch,validity_passed=valid,oracle_ceiling_pass=bool(oracle_pass),streaming_paired_success_pass=bool(stream_pass),noninferiority=bool(noninferior),joint_over_present_lower95=lo,joint_proper_score_increases=increases,event_gates=bool(event_pass),latency_pass=bool(latency),control_pass=controlpass[primary],safety_pass=bool(safety_pass),boundary_localization=dict(localized=bool(localized),wrong_matched_events=len(diagnostic),fraction_with_different_bounds=wrong_fraction,oracle_pitch_accuracy=ov['pitch_accuracy'],stream_pitch_accuracy=ev['pitch_accuracy']),next={'A':'After review PM may assign controlled isolated-voice transformations.','B':'Do not advance complexity; after review PM may assign targeted event-formation repair with fresh groups.','C':'Ceiling failed; retain prior bounded claim, PM chooses different task/readout prerequisite after review.','inconclusive':'No forced localization; PM chooses a discriminating bounded next action.','invalid':'Preserve invalid evidence; stop and report gate failure.'}[branch]);dump(out/'decision.json',decision);print(json.dumps(safe(decision)))
if __name__=='__main__':
    import sys;main(sys.argv[1])
