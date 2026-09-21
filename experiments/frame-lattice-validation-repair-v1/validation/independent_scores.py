"""Independent saved forecast score arithmetic, standard library only."""
import json,csv,gzip,math,sys
from collections import defaultdict
from pathlib import Path
P=Path(__file__).resolve().parent.parent
S=sys.argv[1] if len(sys.argv)>1 else 'heldout'
truth={r['episode']:r for r in map(json.loads,gzip.open(P/'data'/S/'truth.jsonl.gz','rt'))};trials={(r['model'],r['group'],r['cell'],r['condition'],int(r['variant'])):r for r in csv.DictReader((P/'results'/S/'trials.csv').open())};count=0;error=0.
for x in map(json.loads,gzip.open(P/'data'/S/'cache.jsonl.gz','rt')):
 t=truth[x['episode']]
 for front,forecasts in {**x['operational']['forecasts'],'oracle-boundary':x['oracle_forecasts']}.items():
  for name,f in forecasts.items():
   probabilities=defaultdict(float)
   if f['anchor_semitones'] is None:probabilities['unknown']=1.
   else:
    for j,mass in enumerate(f['probabilities']):
     pitch=None if j==49 else round(f['anchor_semitones']+j-24);probabilities[pitch if pitch is not None and -48<=pitch<=72 else 'unknown']+=mass
   target=defaultdict(float)
   for d,m in zip(t['outcome_intervals'],t['outcome_probabilities']):target[round(t['prefix_true_pitches'][-1]+d)]+=m
   loss=sum(-m*math.log(probabilities[k]) if probabilities[k]>0 else math.inf for k,m in target.items());brier=1+sum(v*v for v in probabilities.values())-2*sum(v*probabilities[k] for k,v in target.items());accuracy=float(f['point_pitch_semitones'] is not None and abs(f['point_pitch_semitones']-t['pitch_semitones'])<=.35);r=trials[(front+'/'+name,t['group'],t['cell'],t['condition'],t['variant'])]
   for key,v in [('accuracy',accuracy),('log_loss',loss),('brier',brier)]:
    vv=float(r[key]);e=0. if v==vv else abs(v-vv);assert e<=1e-12;error=max(error,e)
   count+=1
out={'all_pass':True,'forecasts':count,'max_score_error':error,'acoustic_or_model_calls':0};(P/'validation'/('independent_scores_'+S+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
