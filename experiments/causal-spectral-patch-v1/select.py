"""One development selection, no audio/model calls."""
from pathlib import Path
import json,numpy as np
from records import read_lines
from scoring import measure
from patch_labels import assess
P=Path(__file__).resolve().parent;cfg=json.loads((P/'initial_model.json').read_text());assert json.loads((P/'validation/development.json').read_text())['all_pass'];truth={x['episode']:x for x in map(json.loads,read_lines(P/'data/development/truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(P/'data/development/cache.jsonl.gz')));rows=[]
for name in ['single','multi']:
 source=[];brier=[];state=[];compute=[]
 for x in cache:
  t=truth[x['episode']]
  if t['condition']!='intact':continue
  p=x['operational'];f=p['patch_forecasts'][name]['reference'];source.append(assess(f,t)['source_accuracy']);brier.append(measure(f,t)['brier']);state.append(len(json.dumps([{k:z['channels'][k] for k in (['s64'] if name=='single' else ['s64','s128'])} for z in p['patch_frames']]).encode()));compute.append(p['patch_readout_compute_ns'][name])
 rows.append({'id':name,'source':float(np.mean(source)),'brier':float(np.mean(brier)),'mean_serialized_channels_bytes':float(np.mean(state)),'mean_readout_ns':float(np.mean(compute))})
best=min(rows,key=lambda r:(-r['source'],r['brier'],r['mean_serialized_channels_bytes'],r['mean_readout_ns']));cfg['patch_development']=False;cfg['selected_patch']=best['id'];(P/'calibration_model.json').write_text(json.dumps(cfg,separators=(',',':')));(P/'development_selection.json').write_text(json.dumps({'candidates':rows,'selected':best,'rule':'validity; max correct source across balanced cells; min forecast Brier; least measured state then compute'},indent=2));print(best)
