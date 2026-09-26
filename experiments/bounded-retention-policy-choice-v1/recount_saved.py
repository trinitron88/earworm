"""Small raw-response recount independent of score.py and the matcher."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
out={}
for policy in ['fifo','reservoir','diversity','unpressured','present']:
 cells={c:{'n':0,'accepted':0,'source_center':0,'joint_pitch':0,'joint_scale':0,'joint_all':0,'source_retained':0,'reasons':{}} for c in ['unchanged','transpose','stretch','foil','removed']}
 for s in json.loads((ROOT/'input-manifest.json').read_text())['sessions']:
  if s['split']!='evaluation':continue
  label=json.loads((ROOT/s['path']/'labels.json').read_text())
  for mode in (['full'] if s['cell']=='foil' else ['full','removed']):
   p=ROOT/'outputs/evaluation'/s['session_id']/policy/mode
   assert (p/'completed.json').exists()
   r=json.loads((p/'response.json').read_text());raw=r['raw'];v=cells['removed' if mode=='removed' else s['cell']];v['n']+=1
   accepted=raw['accepted'];v['accepted']+=accepted;v['source_retained']+=any(x['id']==1 for x in r['retained_records']);v['reasons'][raw['reason']]=v['reasons'].get(raw['reason'],0)+1
   h=raw.get('selected');truth=accepted and 0<=h['center']<3 and s['cell']!='foil' and mode=='full'
   v['source_center']+=truth
   pitch=truth and h['shift']==label['expected_shift'];scale=truth and abs(h['scale']/label['expected_scale']-1)<=.1
   v['joint_pitch']+=pitch;v['joint_scale']+=scale;v['joint_all']+=pitch and scale
 out[policy]=cells
scored=json.loads((ROOT/'score-evaluation.json').read_text())
for policy,cells in out.items():
 m=scored['metrics'][policy]
 for cell in ['unchanged','transpose','stretch']:
  c=cells[cell];x=m['positive'][cell]
  assert c['source_center']==x['identity_correct'] and c['joint_pitch']==x['joint_pitch_correct'] and c['joint_scale']==x['joint_scale_correct'] and c['joint_all']==x['joint_all_correct']
 assert cells['foil']['accepted']==m['foil_accepted'] and cells['removed']['accepted']==m['removed_accepted']
(ROOT/'independent-recount.json').write_text(json.dumps({'agrees':True,'counted_readouts':560,'method':'Saved raw accepted flag and center within first0–3s source support, exact label shift,10% scale; no imports from main scorer/worker/matcher.','counts':out},indent=2)+'\n')
print(json.dumps({'agrees':True,'readouts':560}))
