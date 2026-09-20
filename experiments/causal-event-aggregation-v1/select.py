"""Select one declared aggregation policy from saved development only."""
from pathlib import Path
import json,numpy as np
from records import read_lines
from events import event_metrics
from scoring import measure,safe
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'initial_model.json').read_text());d=HERE/'data/development';truth={x['episode']:x for x in map(json.loads,read_lines(d/'truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(d/'cache.jsonl.gz')));rows=[]
for index,policy in enumerate(cfg['aggregation_grid']):
 by={}
 for x in cache:
  t=truth[x['episode']];r=by.setdefault(t['group'],{'pitch':[],'available':[],'brier':[]});e=event_metrics(x['operational']['events'][policy['id']],t['bounds'],t['reset_sample']);r['pitch'].append(e['pitch_accuracy']);r['available'].append(e['pitch_availability'])
  if t['condition']=='intact':r['brier'].append(measure(x['operational']['forecasts'][policy['id']]['reference'],t)['brier'])
 r={k:float(np.mean([np.mean(v[k]) for v in by.values()])) for k in ['pitch','available','brier']};r.update(id=policy['id'],complexity=index,feasible=r['available']>=.8);rows.append(r)
feasible=[r for r in rows if r['feasible']];best=min(feasible,key=lambda r:(-r['pitch'],r['brier'],r['complexity'])) if feasible else None
result={'grid':rows,'selected':best,'objective':'availability>=.80 and valid evidence; maximize group pitch accuracy, minimize intact MAP-reference Brier, then declared simpler a32_48 before a48_64'};(HERE/'development_selection.json').write_text(json.dumps(safe(result),indent=2)+'\n');print(json.dumps(result))
if best:
 cfg['selected_aggregation']=best['id'];cfg['aggregation_development']=False;(HERE/'frozen_model.json').write_text(json.dumps(cfg,indent=2)+'\n')
