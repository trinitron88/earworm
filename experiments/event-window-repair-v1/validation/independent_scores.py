"""Independent stdlib score arithmetic on saved forecasts; no acoustic calls."""
import json,csv,math,gzip
from pathlib import Path
from collections import defaultdict
P=Path(__file__).resolve().parent.parent
truth={r['episode']:r for r in map(json.loads,gzip.open(P/'data/heldout/truth.jsonl.gz','rt').read().splitlines())};cfg=json.loads((P/'frozen_model.json').read_text());trials={(r['model'],r['group'],r['cell'],r['condition'],int(r['variant'])):r for r in csv.DictReader((P/'results/heldout/trials.csv').open())};error=0.;count=0;totals=defaultdict(lambda:[0,0])
for x in map(json.loads,gzip.open(P/'data/heldout/cache.jsonl.gz','rt').read().splitlines()):
 t=truth[x['episode']];outputs={'repaired':x['operational']['forecasts'][cfg['selected_support']],'streaming':x['operational']['forecasts'][cfg['selected']],'fixed':x['operational']['forecasts']['fixed'],'oracle-boundary':x['oracle_forecasts']}
 for front,fs in outputs.items():
  for name,f in fs.items():
   p=defaultdict(float)
   if f['anchor_semitones'] is None:p['unknown']=1.
   else:
    for j,mass in enumerate(f['probabilities']):
     pitch=None if j==49 else round(f['anchor_semitones']+j-24);p[pitch if pitch is not None and -48<=pitch<=72 else 'unknown']+=mass
   target=defaultdict(float)
   for delta,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):target[round(t['prefix_true_pitches'][-1]+delta)]+=mass
   ll=sum(-mass*math.log(p[k]) if p[k]>0 else math.inf for k,mass in target.items());brier=1+sum(v*v for v in p.values())-2*sum(v*p[k] for k,v in target.items());correct=float(f['point_pitch_semitones'] is not None and abs(f['point_pitch_semitones']-t['pitch_semitones'])<=.35);model=front+'/'+name;r=trials[(model,t['group'],t['cell'],t['condition'],t['variant'])]
   for k,v in [('accuracy',correct),('log_loss',ll),('brier',brier)]:
    other=float(r[k]);e=0. if v==other else abs(v-other);assert e<1e-12;error=max(error,e)
   if t['condition']=='intact':totals[model+'/'+t['cell']][0]+=int(correct);totals[model+'/'+t['cell']][1]+=1
   count+=1
result={'all_pass':True,'forecasts':count,'max_score_error':error,'intact_correct_total':dict(totals),'audio_or_model_calls':0};(P/'validation/independent_scores.json').write_text(json.dumps(result,indent=2));print(count,error)
