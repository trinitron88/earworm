"""Development-only lattice configuration selection."""
from pathlib import Path
import json,numpy as np
from records import read_lines
from scoring import measure
from lattice_validation import recognition
P=Path(__file__).resolve().parent;cfg=json.loads((P/'initial_model.json').read_text());truth={x['episode']:x for x in map(json.loads,read_lines(P/'data/development/truth.jsonl.gz'))};rows=[];cache=list(map(json.loads,read_lines(P/'data/development/cache.jsonl.gz')))
for q in cfg['lattice_grid']:
 by={}
 for x in cache:
  t=truth[x['episode']]
  if t['condition']!='intact':continue
  f=x['operational']['forecasts'][q['id']]['reference'];z=by.setdefault(t['group'],{'source':[],'brier':[],'coverage':[]});m=recognition(f,t);z['source'].append(m['source_accuracy']);z['brier'].append(measure(f,t)['brier']);z['coverage'].append(m['alignment_coverage'])
 r={k:float(np.mean([np.mean(z[k]) for z in by.values()])) for k in ['source','brier','coverage']};r.update(id=q['id'],samples=q['samples'],feasible=r['coverage']>=.50);rows.append(r)
best=min([r for r in rows if r['feasible']],key=lambda r:(-r['source'],r['brier'],r['samples'])) if any(r['feasible'] for r in rows) else None
(P/'development_selection.json').write_text(json.dumps({'grid':rows,'selected':best,'objective':'validity and matched-query coverage>=.50; max source accuracy; min intact reference Brier; shortest window'},indent=2)+'\n');print(json.dumps({'grid':rows,'selected':best}))
if best:cfg['lattice_development']=False;cfg['selected_lattice']=best['id'];(P/'frozen_model.json').write_text(json.dumps(cfg,indent=2)+'\n')
