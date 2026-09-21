"""Frozen saved-only lattice scoring and decision; no acoustic calls."""
import json,csv,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from records import read_lines
from scoring import measure,safe,absolute_distribution
from patch_labels import assess as recognition
P=Path(__file__).resolve().parent;CELLS=['unchanged','transpose','stretch','timbre']
def dump(p,v):p.write_text(json.dumps(safe(v),indent=2,allow_nan=False)+'\n')
def table(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows([{k:safe(v) for k,v in r.items()} for r in rows])
def main(split):
 d=P/'data'/split;out=P/'results'/split;out.mkdir(parents=True,exist_ok=True);cfg=json.loads((d/'config_used.json').read_text());truth={x['episode']:x for x in map(json.loads,read_lines(d/'truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(d/'cache.jsonl.gz')));rows=[];recognitions=[];pred={};latencies=[]
 for x in cache:
  t=truth[x['episode']];fs={**x['operational']['forecasts'],**{'patch-'+k:v for k,v in x['operational']['patch_forecasts'].items()},'oracle-boundary':x['oracle_forecasts']}
  for front,forecasts in fs.items():
   for name,f in forecasts.items():
    model=front+'/'+name;pr=absolute_distribution(f);r=dict(model=model,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**measure(f,t),entropy=-sum(v*math.log(v) for v in pr if v>0),unknown_mass=pr[-1],confidence=max(pr));rows.append(r);pred[(model,t['group'],t['cell'],t['condition'],t['variant'])]=f
    if front.startswith('patch-') and name in ['reference','absolute']:recognitions.append(dict(model=model,group=t['group'],cell=t['cell'],condition=t['condition'],variant=t['variant'],**recognition(f,t)))
  latencies.extend((f['available_sample']-f['end_sample'])/16000 for f in x['operational']['patch_frames'])
 table(out/'trials.csv',rows);table(out/'recognition_trials.csv',recognitions);groups=sorted({r['group'] for r in rows});models=sorted({r['model'] for r in rows});draw=np.random.default_rng(202609219150).integers(0,len(groups),(5000,len(groups)))
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
 for key,rs in recbucket.items():rg.append(dict(zip(['model','group','cell','condition'],key),**{k:float(np.mean([r[k] for r in rs])) for k in ['source_accuracy','false_match','rejection','pitch_accuracy','time_accuracy','timbre_accuracy','alignment_coverage']}))
 table(out/'recognition_groups.csv',rg)
 rs=[]
 for key in sorted({(r['model'],r['cell'],r['condition']) for r in rg}):
  z=[r for r in rg if (r['model'],r['cell'],r['condition'])==key];rs.append(dict(zip(['model','cell','condition'],key),**{k:float(np.mean([r[k] for r in z])) for k in ['source_accuracy','false_match','rejection','pitch_accuracy','time_accuracy','timbre_accuracy','alignment_coverage']}))
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
   tv=[sum(abs(a-b) for a,b in zip(absolute_distribution(pred[(model,g,'unchanged',cond,0)]),absolute_distribution(pred[(model,g,'unchanged',cond,1)])))/2 for g in groups];acc=float(vec(model,'unchanged',cond,'accuracy').mean());paired=float(vec(model,'unchanged',cond,'paired_success').mean());det[cond]={'accuracy':acc,'paired_success':paired,'tv':max(tv),'pass':acc<=.55 and paired<=.1 and max(tv)<=1e-9}
  err=max(max(abs(a-b) for a,b in zip(absolute_distribution(pred[(model,g,'unchanged','swap',v)]),absolute_distribution(pred[(model,g,'unchanged','intact',1-v)]))) for g in groups for v in [0,1]);paired=float(vec(model,'unchanged','swap','paired_success').mean());det['swap']={'error':err,'paired_success':paired,'pass':err<=1e-9 and paired>=.8};drop=float((vec(model,'unchanged','intact','accuracy')-vec(model,'unchanged','shuffle','accuracy')).mean());det['shuffle']={'drop':drop,'pass':drop<=.1};ar=[]
  for g in groups:
   for v in [0,1]:
    t=truth[f'{g}/joint/ambiguous/{v}'];p=absolute_distribution(pred[(model,g,'unchanged','ambiguous',v)]);ix=[round(t['prefix_true_pitches'][-1]+delta)+48 for delta in t['outcome_intervals']];mass=sum(p[i] for i in ix);dev=max(abs(p[i]-.5) for i in ix);mx=max(p);ar.append({'group':g,'variant':v,'mass':mass,'deviation':dev,'maximum':mx,'pass':mass>=.9 and dev<=.1 and mx<=.6})
  det['ambiguous']={'pass':all(z['pass'] for z in ar),'records':ar};controls.append({'model':model,'details':det,'pass':all(v['pass'] for v in det.values())})
 dump(out/'controls.json',controls)
 primary='patch-'+cfg['selected_patch']+'/reference';oracle='oracle-boundary/reference'
 def aggregate(m,metric='accuracy'):return np.mean([vec(m,c,'intact',metric) for c in CELLS],axis=0)
 competitors=[m for m in models if not m.startswith('oracle-boundary/') and m!=primary];strongest=max(competitors,key=lambda m:(float(aggregate(m).mean()),m));contrasts=[]
 for c in CELLS:
  for comparator in [oracle,strongest]:
   a=vec(primary,c,'intact','accuracy')-vec(comparator,c,'intact','accuracy');lo,hi=ci(a,(.003125,.996875));contrasts.append({'cell':c,'comparator':comparator,'difference':float(a.mean()),'lower_familywise95':lo,'upper_familywise95':hi})
 table(out/'comparisons.csv',contrasts)
 meta={g['group_id']:g for g in json.loads((P/'split_manifest.json').read_text())['groups']};safety=[]
 for model in models:
  for family in ['pure','fundamental','overtone']:
   ix=[i for i,g in enumerate(groups) if meta[g]['family']==family];loss=float((aggregate(oracle)-aggregate(model))[ix].mean());safety.append({'model':model,'family':family,'accuracy_loss_vs_oracle':loss,'pass':loss<=.1})
 dump(out/'safety.json',safety)
 source=[r for r in rs if r['model']==primary and r['condition']=='intact'];overall=float(np.mean([r['source_accuracy'] for r in source]));reject=next(r['false_match'] for r in rs if r['model']==primary and r['condition']=='unrelated');sourcepass=overall>=.9 and min(r['source_accuracy'] for r in source)>=.8 and reject<=.1
 transforms={cell:next(r[metric] for r in source if r['cell']==cell) for cell,metric in [('transpose','pitch_accuracy'),('stretch','time_accuracy'),('timbre','timbre_accuracy')]};transformpass=all(x>=.8 for x in transforms.values());pairs=all(vec(primary,c,'intact','paired_success').mean()>=.8 for c in CELLS);ni=all(r['lower_familywise95']>=-.1 for r in contrasts);oraclepass=all(vec(oracle,c,'intact','paired_success').mean()>=.8 for c in CELLS)
 presentlo=ci(aggregate(primary)-aggregate('patch-'+cfg['selected_patch']+'/present'))[0];removallo=ci(vec(primary,'unchanged','intact','accuracy')-vec(primary,'unchanged','removal','accuracy'))[0];history=presentlo>0 and removallo>0
 control=next(r for r in controls if r['model']==primary);causal=all(v['pass'] for k,v in control['details'].items() if k!='ambiguous');ambiguity=control['details']['ambiguous']['pass'];safe_pass=all(r['pass'] for r in safety if r['model']==primary);increase={m:float((aggregate(primary,m)-aggregate(oracle,m)).mean()) for m in ['log_loss','brier']};proper=increase['log_loss']<=.10 and increase['brier']<=.02
 records=[json.loads(z)['record'] for z in read_lines(d/'events.jsonl.gz')];fd={r['episode']:r['monotonic_ns'] for r in records if r['kind']=='forecast_dispatch'};compute=max((r['monotonic_ns']-fd[r['episode']])/1e9 for r in records if r['kind']=='forecast_commit');latency=max(latencies)<=.16 and compute<=.16;valid=json.loads((P/'validation'/f'{split}.json').read_text())['all_pass'];capture=all(r['silence_status']=='captured_silence' and r['missing_forecasts_unknown'] and r['restored_original_bytes'] for r in records if r['kind']=='silence_missing_probe')
 if not valid:branch='invalid'
 elif not all([oraclepass,sourcepass,history,ni,causal,safe_pass,latency,capture,pairs]):branch='C'
 elif transformpass and proper and ambiguity:branch='A'
 else:branch='B'
 decision={'branch':branch,'validity_passed':valid,'oracle_pass':bool(oraclepass),'source_accuracy':overall,'unrelated_false_match':reject,'source_pass':bool(sourcepass),'separate_transformation_accuracy':transforms,'transformation_pass':bool(transformpass),'paired_success_pass':bool(pairs),'noninferiority':bool(ni),'strongest_comparator':strongest,'aggregate_difference_strongest':float((aggregate(primary)-aggregate(strongest)).mean()),'present_advantage_lower95':presentlo,'removal_advantage_lower95':removallo,'history_dependence_pass':bool(history),'aggregate_proper_score_increases':increase,'causal_controls_pass':bool(causal),'ambiguity_pass':bool(ambiguity),'silence_missing_pass':bool(capture),'safety_pass':bool(safe_pass),'max_feature_sample_latency_s':max(latencies),'max_forecast_compute_s':compute,'latency_pass':bool(latency),'next':{'A':'Retain versioned spectral representation; next isolated-voice stage requires PM assignment after review.','B':'Observation/identity candidate only; next bounded readout/calibration decision belongs to PM.','C':'Reject candidate and end handcrafted synthetic continuous-front sequence; no automatic fourth front.','invalid':'Preserve evidence and stop without rerun/repair.'}[branch]};dump(out/'decision.json',decision);print(json.dumps(safe(decision)))
if __name__=='__main__':
 import sys;main(sys.argv[1])
