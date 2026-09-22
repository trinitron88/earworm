"""Saved-only packaging, resource accounting and frozen analysis; never runs audio."""
import argparse,datetime,json,sys,time
from pathlib import Path
import numpy as np
from analyze import select,analyze
from validate import validate
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def summarize(split):
 d=ROOT/'results'/split;records=load(d/'records.json');summaries=load(d/'summaries.json')
 validation=validate(d);dump(d/'validation.json',validation)
 if split=='development':dump(ROOT/'selection.json',select(records))
 selection=load(ROOT/'selection.json')
 # Conservative wall-time charge covers this active preparation plus every local job
 # launched within it, with a separate additive charge for measured concurrent jobs.
 active=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime(2026,9,22,14,45,11,72000,tzinfo=datetime.timezone.utc)).total_seconds()
 prior=861.146346
 allsummaries=[]
 for which in ('development','evaluation'):
  p=ROOT/'results'/which/'summaries.json'
  if p.exists():allsummaries+=load(p)
 routes={}
 for route in ('standard',selection['selected_mert'],'ceiling'):
  rows=[r for r in records if r['route']==route]
  full=[r for r in rows if r['condition']=='full']
  if route=='ceiling':
   peak=max(sum(a.nbytes+sys.getsizeof(a) for a in np.load(d/(s['group']+'-'+s['cell'])/'ceiling.npz').values()) for s in summaries)
  else:peak=max(s['finish']['peak_state_bytes'] for s in summaries)
  routes[route]={'max_decision_latency_seconds':max(r['prediction']['decision_latency_seconds'] for r in rows),'extraction_matching_rtf':max(r['prediction']['rtf'] for r in rows),'peak_persistent_bytes':peak,'raw_ring_seconds':0 if route=='ceiling' else 4,'raw_ring_chunks':0 if route=='ceiling' else 4,'extraction_unit_seconds':1,'end_to_end_compute_seconds':sum(r['prediction']['end_to_end_compute_seconds'] for r in full),'unit_replacements':max(s['finish']['unit_replacements'] for s in summaries),'model_weights_bytes':377552987 if route.startswith('mert') else 0}
 size=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 resource={'executions':sum(s['executions'] for s in allsummaries)+40,'actual_music_readouts':sum(s['executions'] for s in allsummaries),'conservative_qualification_probe_charge':40,'qualification_note':'40 reserved/charged for all preparation, parser/matcher/material/analysis fixtures and saved-only verification calls; planned music readouts960 leave no extra audio/model execution allowance. Completed initial MERT probe is reused.','aggregate_compute_seconds':prior+active+4*sum(s['session_wall_seconds'] for s in allsummaries)+30,'prior_conservative_charge_seconds':prior,'active_preparation_wall_seconds':active,'concurrent_run_additive_seconds':4*sum(s['session_wall_seconds'] for s in allsummaries),'run_charge_note':'Four times session wall seconds additionally charged for multithreaded/overlapping local computation; active preparation wall already includes these sessions.','additional_parallel_fixture_reserve_seconds':30,'new_artifact_bytes':size,'external_spend_usd':0,'acquisition_bytes':123847,'routes':routes,'peak_listener_rss_bytes':max(s['peak_rss_bytes'] for s in summaries),'scratch_note':'Listener peak RSS includes fixed encoder, raw ring, persistent state, temporary tensors and serialization/readout copies. Persistent state is separately structurally measured; RSS is not presented as an exact allocator scratch difference.','capacity_pressure':False}
 checks={k:validation[k] for k in ('software','provenance','access','eviction','evidence','preservation')};checks.update(expected_groups=8 if split=='development' else 16,selected_mert=selection['selected_mert'])
 report=analyze(records,selection,checks,resource);dump(d/'resources.json',resource);dump(d/'analysis.json',report)
 if split=='development':
  projected_bytes=size+2*sum(p.stat().st_size for p in d.rglob('*') if p.is_file())+64*1024**2
  reserve_seconds=64*max(s['session_wall_seconds'] for s in summaries)*5+600
  forecast={'remaining_evaluation_sessions':64,'remaining_evaluation_readouts':576,'projected_total_executions':resource['executions']+576,'projected_artifact_bytes':projected_bytes,'reserved_eval_compute_seconds':reserve_seconds,'projected_aggregate_seconds':resource['aggregate_compute_seconds']+reserve_seconds,'fit':resource['executions']+576<=1000 and projected_bytes<=2*1024**3 and resource['aggregate_compute_seconds']+reserve_seconds<=7200,'development_schema_complete':not report['schema_errors'],'validation_pass':all(checks[k] is True for k in ('software','provenance','access','eviction','evidence','preservation'))}
  dump(ROOT/'preflight.json',forecast)
 print(json.dumps({'split':split,'decision':report['decision'],'selected_mert':selection['selected_mert'],'thresholds':selection['thresholds'],'validation':checks,'executions':resource['executions'],'compute_charge':resource['aggregate_compute_seconds'],'bytes':size,'schema_errors':report['schema_errors'],'invalid_reasons':report['invalid_reasons']},indent=2))
if __name__=='__main__':summarize(sys.argv[1])
