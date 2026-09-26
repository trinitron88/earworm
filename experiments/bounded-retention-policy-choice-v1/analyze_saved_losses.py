"""Saved-ledger interpretation only: no predictor/model call."""
import gzip,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'input-manifest.json').read_text())['sessions'];losses=[];misses=[]
for s in manifest:
 if s['split']!='evaluation' or s['cell']=='foil':continue
 observations=json.loads((ROOT/s['path']/'observations.json').read_text())
 for policy in ['fifo','reservoir','diversity']:
  dest=ROOT/'outputs/evaluation'/s['session_id']/policy/'full'
  with gzip.open(dest/'arrivals.jsonl.gz','rt') as f:
   lost=[v['receipt']['available_at'] for line in f if (v:=json.loads(line))['receipt'].get('completion') and v['receipt']['completion'].get('evicted_id')==1]
  response=json.loads((dest/'response.json').read_text())
  assert len(lost)==1 and not any(r['id']==1 for r in response['retained_records'])
  losses.append({'family':s['family_id'],'cell':s['cell'],'policy':policy,'source_evicted_at':lost[0],'query_onset':observations['query']['support'][0],'source_still_available':False})
 dest=ROOT/'outputs/evaluation'/s['session_id']/'unpressured/full';r=json.loads((dest/'response.json').read_text())
 if not r['raw']['accepted']:
  h=observations['occurrences'][0]['events'];q=observations['query']['events'];a=(q[-1][1]-q[0][0])/(h[-1][1]-h[0][0]);b=q[0][0]-a*h[0][0];shift=q[0][2]-h[0][2]
  residual=max(abs(q[i][j]-(a*h[i][j]+b)) for i in range(12) for j in [0,1]);assert residual<=1e-9 and all(q[i][2]-h[i][2]==shift for i in range(12))
  misses.append({'family':s['family_id'],'cell':s['cell'],'reason':r['raw']['reason'],'candidate_count':r['raw']['candidate_count'],'source_record_retained':any(x['id']==1 for x in r['retained_records']),'independent_full_event_affine_residual_seconds':residual,'independent_shift':shift,'independent_scale':a,'response_path':str((dest/'response.json').relative_to(ROOT))})
(ROOT/'retention-losses.json').write_text(json.dumps({'rows':losses,'scope':'All48 held-out positive cells per bounded policy; occurrence1 held exact source events.','future_access_used':False},indent=2)+'\n')
(ROOT/'unpressured-misses.json').write_text(json.dumps({'rows':misses,'count':len(misses),'interpretation':'Source evidence survives but frozen G returns no candidate despite independently compatible full construction under arithmetic tolerance. Does not isolate a cause; no counterfactual matcher call or repair.'},indent=2)+'\n')
print(json.dumps({'losses':len(losses),'unpressured_misses':len(misses),'range_by_policy':{p:[min(x['source_evicted_at'] for x in losses if x['policy']==p),max(x['source_evicted_at'] for x in losses if x['policy']==p)] for p in ['fifo','reservoir','diversity']}}))
