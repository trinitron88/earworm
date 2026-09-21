"""One finite scalar fit on saved calibration readouts; no acoustic rerun."""
from pathlib import Path
import json,math,numpy as np
from records import read_lines
from scoring import measure,safe
P=Path(__file__).resolve().parent;cfg=json.loads((P/'calibration_model.json').read_text());assert json.loads((P/'validation/calibration.json').read_text())['all_pass'];truth={x['episode']:x for x in map(json.loads,read_lines(P/'data/calibration/truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(P/'data/calibration/cache.jsonl.gz')));rows=[]
for temp in [.015,.025,.05]:
 losses=[];briers=[]
 for x in cache:
  t=truth[x['episode']]
  if t['condition']!='intact':continue
  f=dict(x['operational']['patch_forecasts'][cfg['selected_patch']]['reference']);cs=f['lookup_evidence']
  if cs:
   p=[0.]*50;weights=[math.exp(-c['cost']/temp) for c in cs];sw=sum(weights)
   for c,w in zip(cs,weights):
    delta=c['prediction_pitch']-f['anchor_semitones'];mass=[math.exp(-.5*((j-delta)/.08)**2) for j in range(-24,25)];sm=sum(mass)
    if sm:
     for j,m in enumerate(mass):p[j]+=w/sw*m/sm
    else:p[-1]+=w/sw
   f['probabilities']=[.999*v+.001/50 for v in p]
  m=measure(f,t);losses.append(m['log_loss']);briers.append(m['brier'])
 rows.append({'temperature':temp,'log_loss':float(np.mean(losses)),'brier':float(np.mean(briers))})
best=min(rows,key=lambda r:(r['log_loss'],r['brier'],abs(r['temperature']-.025),r['temperature']));cfg['patch_temperature']=best['temperature'];(P/'frozen_model.json').write_text(json.dumps(cfg,separators=(',',':')));(P/'calibration_fit.json').write_text(json.dumps(safe({'grid':rows,'selected':best,'rule':'min mean intact logloss; Brier tie break; closest initial temperature then lower'}),indent=2));print(safe(best))
