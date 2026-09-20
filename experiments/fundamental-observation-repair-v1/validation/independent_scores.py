"""Stdlib-only reconstruction of saved common-coordinate scoring; no audio work."""
import json,math,csv
from pathlib import Path
from collections import defaultdict
P=Path(__file__).resolve().parent.parent
truth={r['episode']:r for r in map(json.loads,(P/'data/heldout/truth.jsonl').read_text().splitlines())}
trials={(r['model'],r['group'],r['cell'],r['condition'],int(r['variant'])):r for r in csv.DictReader((P/'results/heldout/trials.csv').open())}
errors=[];n=0;counts=defaultdict(lambda:[0,0])
for x in map(json.loads,(P/'data/heldout/arrived_cache.jsonl').read_text().splitlines()):
 t=truth[x['episode']]
 for name,f in x['forecast']['forecasts'].items():
  p=defaultdict(float)
  if f['anchor_semitones'] is None:p['unknown']=1.
  else:
   for j,mass in enumerate(f['probabilities']):
    pitch=None if j==49 else round(f['anchor_semitones']+j-24)
    p[pitch if pitch is not None and -48<=pitch<=72 else 'unknown']+=mass
  target=defaultdict(float)
  for delta,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):target[round(t['prefix_true_pitches'][-1]+delta)]+=mass
  ll=sum(-mass*math.log(p[key]) if p[key]>0 else math.inf for key,mass in target.items())
  brier=1+sum(v*v for v in p.values())-2*sum(m*p[k] for k,m in target.items())
  correct=float(f['point_pitch_semitones'] is not None and abs(f['point_pitch_semitones']-t['pitch_semitones'])<=.35)
  r=trials[(name,t['group_id'],t['family'],t['condition'],t['variant'])]
  for key,value in [('accuracy',correct),('log_loss',ll),('brier',brier)]:
   other=float(r[key]);error=0 if value==other else abs(value-other);assert error<1e-12;errors.append(error)
  if t['condition']=='intact':counts[name+'/'+t['family']][0]+=int(correct);counts[name+'/'+t['family']][1]+=1
  n+=1
result={'all_pass':True,'forecasts_scored':n,'maximum_score_error':max(errors),'intact_correct_total':dict(counts),'no_audio_or_model_execution':True}
(P/'validation/independent_scores.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
