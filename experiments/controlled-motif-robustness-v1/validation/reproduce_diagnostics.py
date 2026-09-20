from pathlib import Path
import json,csv,hashlib,datetime,sys,platform
p=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(p))
from verify import reconstruct
cfg=json.loads((p/'frozen_model.json').read_text());truth={x['episode']:x for x in map(json.loads,(p/'data/heldout/truth.jsonl').read_text().splitlines())};caches={x['episode']:x for x in map(json.loads,(p/'data/heldout/arrived_cache.jsonl').read_text().splitlines())};err=0.;n=0;offsets=[]
for r in map(json.loads,(p/'results/heldout/oracle_diagnostic.jsonl').read_text().splitlines()):
 t=truth[r['episode']];pitches=t['prefix_true_pitches'][11:] if t['condition']=='reset' else t['prefix_true_pitches'];h=[{'pitch_semitones':x} for x in pitches]
 for name,f in r['forecasts'].items():
  probs,point,atoms=reconstruct(h,'retrieval_transposed' if name in ['reference','candidate'] else name,cfg['reference' if name=='reference' else 'new']);e=max(abs(a-b) for a,b in zip(probs,f['probabilities']));assert e<1e-12;err=max(err,e);n+=1
 if t['family']=='joint' and t['condition']=='intact' and t['variant']==0:
  x=caches[r['episode']];f=x['forecast']['forecasts']['reference'];offsets.append(dict(group=t['group_id'],anchor_error=f['anchor_semitones']-t['prefix_true_pitches'][-1],lookup_entries=f['matched_memory_entries'],prediction_error=None if f['point_pitch_semitones'] is None else f['point_pitch_semitones']-t['pitch_semitones']))
(p/'validation/oracle_reconstruction.json').write_text(json.dumps({'all_pass':True,'forecasts':n,'max_error':err,'method':'Independent scalar reconstruct from saved arrived fundamentals, same frozen config; no worker API/no audio extraction'},indent=2))
# Only bounded saved anchor/lookup evidence supporting the preregistered diagnostic.
(p/'results/heldout/anchor_lookup_diagnostic.json').write_text(json.dumps(offsets,indent=2))
print(offsets)
