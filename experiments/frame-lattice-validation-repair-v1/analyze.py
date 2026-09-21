"""Frozen saved-only lattice scoring and decision; no acoustic calls."""
import json,csv,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from records import read_lines
from scoring import measure,safe,absolute_distribution
from lattice_validation import recognition
P=Path(__file__).resolve().parent;CELLS=['detached','legato','duration','joint']
def dump(p,v):p.write_text(json.dumps(safe(v),indent=2,allow_nan=False)+'\n')
def table(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows([{k:safe(v) for k,v in r.items()} for r in rows])
def main(split):
 d=P/'data'/split;out=P/'results'/split;out.mkdir(parents=True,exist_ok=True);cfg=json.loads((d/'config_used.json').read_text());truth={x['episode']:x for x in map(json.loads,read_lines(d/'truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(d/'cache.jsonl.gz')));rows=[];recognitions=[];pred={};latencies=[]
 for x in cache:
  t=truth[x['episode']];fs={**x['operational']['forecasts'],'oracle-boundary':x['oracle_forecasts']}
  for front,forecasts in fs.items():
   for name,f in forecasts.items():
    model=front+'/'+name;pr=absolute_distribution(f);r=dict(model=model,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**measure(f,t),entropy=-sum(v*math.log(v) for v in pr if v>0),unknown_mass=pr[-1],confidence=max(pr));rows.append(r);pred[(model,t['group'],t['cell'],t['condition'],t['variant'])]=f
    if front in x['operational']['lattice'] and name in ['reference','absolute','single']:recognitions.append(dict(model=model,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**recognition(f,t)))
  for fr in x['operational']['lattice'].values():latencies.extend((f['available_sample']-f['end_sample'])/16000 for f in fr)
 table(out/'trials.csv',rows);table(out/'recognition_trials.csv',recognitions);groups=sorted({r['group'] for r in rows});models=sorted({r['model'] for r in rows});draw=np.random.default_rng(2026092160).integers(0,len(groups),(5000,len(groups)))
 def ci(x,q=(.025,.975)):return np.quantile(np.array(x)[draw].mean(axis=1),q,method='inverted_cdf').tolist()
 bucket=defaultdict(list)
 for r in rows:bucket[tuple(r[k] for k in ['model','group','cell','condition'])].append(r)
 metrics=['accuracy','log_loss','brier','entropy','unknown_mass','confidence'];gr=[]
 for key,rs in bucket.items():
  assert len(rs)==2;gr.append(dict(zip(['model','group','cell','condition'],key),**{k:float(np.mean([r[k] for r in rs])) for k in metrics},paired_success=float(all(r['accuracy'] for r in rs))))
 table(out/'groups.csv',gr)
 def vec(model,cell,cond,metric):return np.array([next(r[metric] for r in gr if (r['model'],r['group'],r['cell'],r['condition'])==(model,g,cell,cond)) for g in groups])
 summary=[]
 for model,cell,cond in sorted({(r['model'],r['cell'],r['condition']) for r in rows}):
  r=dict(model=model,cell=cell,condition=cond)
  for metric in metrics+['paired_success']:
   a=vec(model,cell,cond,metric);lo,hi=ci(a);r.update({metric:float(a.mean()),metric+'_lower95':lo,metric+'_upper95':hi})
  summary.append(r)
 table(out/'summary.csv',summary)
 recbucket=defaultdict(list)
 for r in recognitions:recbucket[tuple(r[k] for k in ['model','group','cell','condition'])].append(r)
 rg=[]
 for key,rs in recbucket.items():rg.append(dict(zip(['model','group','cell','condition'],key),**{k:float(np.mean([r[k] for r in rs])) for k in ['source_accuracy','false_match','rejection','transformation_accuracy','alignment_coverage']}))
 table(out/'recognition_groups.csv',rg)
 rs=[]
 for key in sorted({(r['model'],r['cell'],r['condition']) for r in rg}):
  z=[r for r in rg if (r['model'],r['cell'],r['condition'])==key];rs.append(dict(zip(['model','cell','condition'],key),**{k:float(np.mean([r[k] for r in z])) for k in ['source_accuracy','false_match','rejection','transformation_accuracy','alignment_coverage']}))
 table(out/'recognition_summary.csv',rs)
 reliability=[]
 for key in sorted({(r['model'],r['cell'],r['condition']) for r in rows}):
  z=[r for r in rows if (r['model'],r['cell'],r['condition'])==key]
  for b in range(10):
   vv=[r for r in z if min(9,int(r['confidence']*10))==b]
   if vv:reliability.append(dict(zip(['model','cell','condition'],key),bin=b,count=len(vv),confidence=float(np.mean([r['confidence'] for r in vv])),accuracy=float(np.mean([r['accuracy'] for r in vv]))))
 table(out/'calibration_bins.csv',reliability)
 controls=[]
 for model in models:
  det={}
  for cond in ['reset','removal']:
   tv=[sum(abs(a-b) for a,b in zip(absolute_distribution(pred[(model,g,'joint',cond,0)]),absolute_distribution(pred[(model,g,'joint',cond,1)])))/2 for g in groups];acc=float(vec(model,'joint',cond,'accuracy').mean());paired=float(vec(model,'joint',cond,'paired_success').mean());det[cond]={'accuracy':acc,'paired_success':paired,'tv':max(tv),'pass':acc<=.55 and paired<=.1 and max(tv)<=1e-9}
  err=max(max(abs(a-b) for a,b in zip(absolute_distribution(pred[(model,g,'joint','swap',v)]),absolute_distribution(pred[(model,g,'joint','intact',1-v)]))) for g in groups for v in [0,1]);paired=float(vec(model,'joint','swap','paired_success').mean());det['swap']={'error':err,'paired_success':paired,'pass':err<=1e-9 and paired>=.8};drop=float((vec(model,'joint','intact','accuracy')-vec(model,'joint','shuffle','accuracy')).mean());det['shuffle']={'drop':drop,'pass':drop<=.1};ar=[]
  for g in groups:
   for v in [0,1]:
    t=truth[f'{g}/joint/ambiguous/{v}'];p=absolute_distribution(pred[(model,g,'joint','ambiguous',v)]);ix=[round(t['prefix_true_pitches'][-1]+delta)+48 for delta in t['outcome_intervals']];mass=sum(p[i] for i in ix);dev=max(abs(p[i]-.5) for i in ix);mx=max(p);ar.append({'group':g,'variant':v,'mass':mass,'deviation':dev,'maximum':mx,'pass':mass>=.9 and dev<=.1 and mx<=.6})
  det['ambiguous']={'pass':all(z['pass'] for z in ar),'records':ar};controls.append({'model':model,'details':det,'pass':all(v['pass'] for v in det.values())})
 dump(out/'controls.json',controls)
 primary=cfg['selected_lattice']+'/reference';oracle='oracle-boundary/reference';contrasts=[]
 for c in CELLS:
  a=vec(primary,c,'intact','accuracy')-vec(oracle,c,'intact','accuracy');lo,hi=ci(a,(.00625,.99375));contrasts.append({'cell':c,'selected_minus_oracle':float(a.mean()),'lower_familywise95':lo,'upper_familywise95':hi})
 table(out/'comparisons.csv',contrasts)
 # All non-oracle competitors except selected transformation-aware reference.
 competitors=[m for m in models if not m.startswith('oracle-boundary/') and m!=primary];strongest=max(competitors,key=lambda m:(float(vec(m,'joint','intact','accuracy').mean()),m));diff=vec(primary,'joint','intact','accuracy')-vec(strongest,'joint','intact','accuracy');lo,hi=ci(diff);presentlo=ci(vec(primary,'joint','intact','accuracy')-vec(cfg['selected_lattice']+'/present','joint','intact','accuracy'))[0]
 meta={g['group_id']:g for g in json.loads((P/'split_manifest.json').read_text())['groups']};safety=[]
 for model in models:
  for family in ['pure','fundamental','overtone']:
   ix=[i for i,g in enumerate(groups) if meta[g]['family']==family];loss=float(np.mean([(vec(oracle,c,'intact','accuracy')-vec(model,c,'intact','accuracy'))[ix].mean() for c in CELLS]));safety.append({'model':model,'family':family,'accuracy_loss_vs_oracle':loss,'pass':loss<=.1})
 dump(out/'safety.json',safety)
 source=[r for r in rs if r['model']==primary and r['condition']=='intact'];overall=float(np.mean([r['source_accuracy'] for r in source]));reject=next(r['false_match'] for r in rs if r['model']==primary and r['condition']=='unrelated');transform=float(np.mean([r['transformation_accuracy'] for r in source if r['cell'] in ['duration','joint']]));sourcepass=overall>=.9 and min(r['source_accuracy'] for r in source)>=.8 and reject<=.1;transformpass=transform>=.8;oraclepass=all(vec(oracle,c,'intact','paired_success').mean()>=.8 for c in CELLS);pairs=all(vec(primary,c,'intact','paired_success').mean()>=.8 for c in CELLS);ni=all(r['lower_familywise95']>=-.1 for r in contrasts);safetypass=all(r['pass'] for r in safety if r['model']==primary);control=next(r for r in controls if r['model']==primary);causalcontrols=all(v['pass'] for k,v in control['details'].items() if k!='ambiguous');ambiguous=control['details']['ambiguous']['pass'];increase={m:float(vec(primary,'joint','intact',m).mean()-vec(oracle,'joint','intact',m).mean()) for m in ['log_loss','brier']};proper=increase['log_loss']<=.1 and increase['brier']<=.02
 records=[json.loads(z)['record'] for z in read_lines(d/'events.jsonl.gz')];fd={r['episode']:r['monotonic_ns'] for r in records if r['kind']=='forecast_dispatch'};compute=max((r['monotonic_ns']-fd[r['episode']])/1e9 for r in records if r['kind']=='forecast_commit');latency=max(latencies)<=.16 and compute<=.16;valid=json.loads((P/'validation'/f'{split}.json').read_text())['all_pass'];advantage=lo>0 and presentlo>0
 if not valid:branch='invalid'
 elif not oraclepass or not sourcepass or not transformpass or not causalcontrols or not safetypass or not advantage or not latency:branch='C'
 elif pairs and ni and proper and ambiguous:branch='A'
 elif not proper or not ambiguous or not pairs or not ni:branch='B'
 else:branch='inconclusive'
 decision={'branch':branch,'validity_passed':valid,'oracle_pass':bool(oraclepass),'source_accuracy':overall,'unrelated_false_match':reject,'source_pass':bool(sourcepass),'transformation_accuracy_changed':transform,'transformation_pass':bool(transformpass),'paired_success_pass':bool(pairs),'noninferiority':bool(ni),'strongest_comparator':strongest,'joint_gain':float(diff.mean()),'joint_gain_lower95':lo,'joint_gain_upper95':hi,'joint_present_lower95':presentlo,'proper_score_increases':increase,'causal_controls_pass':bool(causalcontrols),'ambiguity_pass':bool(ambiguous),'safety_pass':bool(safetypass),'max_feature_sample_latency_s':max(latencies),'max_forecast_compute_s':compute,'latency_pass':bool(latency),'next':{'A':'After review PM may assign bounded transformation recognition.','B':'Lattice candidate only; PM may assign one bounded readout/calibration repair.','C':'Reject lattice and checkpoint continuous-representation prerequisite; no NSDF/window micro-repair.','invalid':'Preserve evidence and stop.','inconclusive':'Preserve evidence; no forced choice.'}[branch]};dump(out/'decision.json',decision);print(json.dumps(safe(decision)))
if __name__=='__main__':
 import sys;main(sys.argv[1])
