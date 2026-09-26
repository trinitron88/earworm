"""Independent evaluator: saved predictions only; never imports the matcher."""
import argparse,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
POLICIES=['fifo','reservoir','diversity','unpressured','present']
POS=['unchanged','transpose','stretch']
def relation(history,query):
 h=np.asarray(history,dtype=float);q=np.asarray(query,dtype=float)
 if h.shape!=(12,3) or q.shape!=(12,3):return None
 shift=q[0,2]-h[0,2];scale=(q[-1,1]-q[0,0])/(h[-1,1]-h[0,0]);offset=q[0,0]-scale*h[0,0]
 residual=float(np.max(np.abs(q[:,:2]-(h[:,:2]*scale+offset))))
 if shift not in range(-5,6) or not .65<=scale<=1.5 or not np.all(q[:,2]-h[:,2]==shift) or residual>1e-9:return None
 return {'shift':int(shift),'scale':float(scale),'offset':float(offset),'residual':residual}
def mapping(candidate,records):
 return [i+1 for i,r in enumerate(records) if r['support'][0]-1e-9<=candidate['start'] and candidate['end']<=r['support'][1]+1e-9 and r['support'][0]<=candidate['center']<r['support'][1]]
def rows_for(split):
 rows=[];manifest=json.loads((ROOT/'input-manifest.json').read_text())['sessions']
 for s in manifest:
  if s['split']!=split:continue
  inp=ROOT/s['path'];obs=json.loads((inp/'observations.json').read_text());label=json.loads((inp/'labels.json').read_text())
  truth={i+1:relation(r['events'],obs['query']['events']) for i,r in enumerate(obs['occurrences'])};truth={i:r for i,r in truth.items() if r is not None}
  for policy in POLICIES:
   for mode in (['full'] if s['cell']=='foil' else ['full','removed']):
    out=ROOT/'outputs'/split/s['session_id']/policy/mode
    if not (out/'completed.json').exists():continue
    response=json.loads((out/'response.json').read_text());raw=response['raw'];candidates=raw['candidates'];retained={r['id'] for r in response['retained_records']}
    sets=[mapping(c,obs['occurrences']) for c in candidates];got={x for a in sets for x in a}
    accepted=bool(raw['accepted']);chosen=sets[0] if accepted and len(sets)==1 else []
    true_candidate=next((x for x in chosen if x in truth and x in retained),None)
    # A chosen origin is not uniquely supported when full observations are equivalent.
    correct=bool(accepted and true_candidate is not None and len(truth)==1 and mode=='full' and s['cell'] in POS)
    transform=truth.get(true_candidate,{})
    selected=raw.get('selected') or {}
    query_support=raw.get('query_support')
    source_expected=None
    if query_support is not None and transform:
     source_expected=[(v-transform['offset'])/transform['scale'] for v in query_support]
    rows.append({'session_id':s['session_id'],'family_id':s['family_id'],'split':split,'stratum':s['stratum'],'cell':s['cell'],'policy':policy,'mode':mode,
      'accepted':accepted,'identity_correct':correct,'stipulated_source_correct':bool(correct and true_candidate==1),
      'joint_pitch_correct':bool(correct and selected.get('shift')==transform['shift']),
      'joint_scale_correct':bool(correct and abs(selected.get('scale',0)/transform['scale']-1)<=.1),
      'joint_all_correct':bool(correct and selected.get('shift')==transform['shift'] and abs(selected.get('scale',0)/transform['scale']-1)<=.1),
      'truth_complete_occurrence_ids':sorted(truth),'truth_retained_ids':sorted(set(truth)&retained),
      'query_compatible_record_ids':sorted(got),'set_contains_complete_truth':bool(set(truth) and set(truth)<=got),
      'complete_truth_set_equal':bool(set(truth) and set(truth)==got),'compatible_set_size':len(got),'candidate_count':len(candidates),'abstained':not accepted,
      'source_retained':1 in retained,'replacements':response['persistent_replacements'],'admission_rejections':response['admission_rejections'],
      'source_absent_recent':all(u>=3 for u in response['recent_units']),
      'localization_start_error':None if not correct else float(selected['start']-source_expected[0]),
      'localization_end_error':None if not correct else float(selected['end']-source_expected[1]),
      'persistent_bytes':response['persistent_bytes'],'peak_persistent_bytes':response['peak_persistent_bytes'],
      'scratch_input_bytes':response['scratch_input_bytes'],'compute_seconds':response['compute_seconds'],
      'output_available_at':response['simulated_delivery_available_at'],'worker_output_available_at':response['output_available_at'],'broker_received_monotonic':response['broker_received_monotonic'],'final_observations_available_at':response['simulation_observations_available_at'],
      'uncertain':raw.get('parameter_uncertain'),'response_path':str((out/'response.json').relative_to(ROOT))})
 return rows

def summarize(rows,n):
 metrics={}
 for policy in POLICIES:
  rr=[r for r in rows if r['policy']==policy];positive={}
  for cell in POS:
   cr=[r for r in rr if r['mode']=='full' and r['cell']==cell]
   positive[cell]={'n':len(cr),**{k:sum(r[k] for r in cr) for k in ['identity_correct','joint_pitch_correct','joint_scale_correct','joint_all_correct','source_retained','set_contains_complete_truth','abstained']}}
  neg=[r for r in rr if r['cell']=='foil'];removed=[r for r in rr if r['mode']=='removed']
  minimum=14 if n==16 else math.ceil(.875*n)
  foilmax=1 if n==16 else 0;remmax=2 if n==16 else 0
  scientific=(len(rr)==n*7 and all(c['n']==n and all(c[k]>=minimum for k in ['identity_correct','joint_pitch_correct','joint_scale_correct']) for c in positive.values()) and sum(r['accepted'] for r in neg)<=foilmax and sum(r['accepted'] for r in removed)<=remmax)
  pressure=all(r['replacements']>=12 for r in rr) if policy in POLICIES[:3] else True
  metrics[policy]={'positive':positive,'foil_accepted':sum(r['accepted'] for r in neg),'foil_n':len(neg),'removed_accepted':sum(r['accepted'] for r in removed),'removed_n':len(removed),'scientific_gates_pass':scientific,'pressure_gates_pass':pressure,'min_replacements':min((r['replacements'] for r in rr),default=0),'max_persistent_bytes':max((r['peak_persistent_bytes'] for r in rr),default=0),'by_stratum':{st:{cell:{'n':sum(r['mode']=='full' and r['cell']==cell and r['stratum']==st for r in rr),'identity':sum(r['identity_correct'] and r['cell']==cell and r['stratum']==st for r in rr),'joint_all':sum(r['joint_all_correct'] and r['cell']==cell and r['stratum']==st for r in rr)} for cell in POS} for st in ['bach','novel']}}
 return metrics

def main():
 ap=argparse.ArgumentParser();ap.add_argument('split',choices=['development','calibration','evaluation']);args=ap.parse_args();n={'development':4,'calibration':4,'evaluation':16}[args.split]
 rows=rows_for(args.split);metrics=summarize(rows,n)
 selected=None;branch='development_only'
 if args.split=='evaluation':
  validation=json.loads((ROOT/'validation-evaluation.json').read_text())
  if len(rows)!=560 or not validation['passed']:branch='INVALID'
  elif not metrics['unpressured']['scientific_gates_pass']:branch='C'
  else:
   passing=[p for p in POLICIES[:3] if metrics[p]['scientific_gates_pass'] and metrics[p]['pressure_gates_pass']]
   branch='A' if passing else 'B';selected=passing[0] if passing else None
 out={'split':args.split,'readouts':len(rows),'metrics':metrics,'selected_branch':branch,'selected_policy':selected,'rows':rows,'limits':'Constructed correspondence, not human perceptual identity. Frozen partial query; exact clean observations and supplied segmentation.'}
 (ROOT/('score-'+args.split+'.json')).write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
