"""Independent saved-output validation. No matcher import, prediction, or replay.

Reconstructs broker clipping and checks the declared ledger against mathematical
policy rules. This is validation arithmetic, never an additional streamed worker
invocation. Runtime guard/no-hidden-cache claims additionally rely on frozen
source inspection; saved receipts alone cannot prove absence of hidden state.
"""
import argparse
import gzip
import hashlib
import json
import math
import random
import time
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
POLICIES=('fifo','reservoir','diversity','unpressured','present')
EXPECTED={'development':140,'calibration':140,'evaluation':560}
SEED=202609260701


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def digest(events,support):
 h=hashlib.sha256();h.update(np.asarray(events,dtype='<f8').tobytes());h.update(np.asarray(support,dtype='<f8').tobytes());return h.hexdigest()
def demand(ok,message):
 if not ok:raise ValueError(message)
def close(a,b,atol=1e-9):return np.shape(a)==np.shape(b) and np.allclose(a,b,rtol=0,atol=atol)
def descriptor(e):
 a=np.asarray(e,dtype=float);return np.r_[np.diff(a[:,2])/12,((a[:,:2]-a[0,0])/(a[-1,1]-a[0,0])).ravel()]
def packet_hash(packet):return hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def input_evidence(obs):
 """Construct expected arrival metadata from immutable observations only."""
 records=[];completions={};packets=[]
 for i,r in enumerate(obs['occurrences']+[obs['query']],1):
  support=[math.floor(r['support'][0]+1e-10),math.ceil(r['support'][1]-1e-10)]
  e=np.asarray(r['events'],dtype=float)
  demand(e.shape==(12,3) and np.isfinite(e).all(),'invalid material events')
  demand(np.all(e[:,1]>e[:,0]) and np.all(e[1:,0]>=e[:-1,1]),'nonmonophonic material')
  record={'id':i,'events':r['events'],'support':support,'hash':digest(e,support),'available_at':support[1],'descriptor':descriptor(e)}
  demand(support[1] not in completions,'two record completions in same unit')
  completions[support[1]]=record;records.append(record)
 events=[e for r in records for e in r['events']];final=records[-1]['support'][1]
 for u in range(final):
  pieces=[e for e in events if e[0]<u+1 and e[1]>u]
  completion=completions.get(u+1)
  msg={'op':'unit','unit':u,'available_at':u+1,
       'events':[[max(a,u),min(b,u+1),p] for a,b,p in pieces],
       'event_left_clipped':[a<u for a,b,p in pieces],
       'event_right_clipped':[b>u+1 for a,b,p in pieces],
       'completed_support':None if completion is None else completion['support']}
  packets.append({'message':msg,'packet_hash':packet_hash(msg),'event_hash':digest(msg['events'],[u,u+1]),'completion':completion})
 return records,packets


def policy_ledger(records,policy):
 """Independent arithmetic check of fixed policy decisions; not a worker run."""
 kept=[];rng=random.Random(SEED);replacements=0;rejections=0;out={}
 cap=512 if policy=='unpressured' else 8
 for r in records:
  entry={'arrived_id':r['id'],'events_sha256':r['hash'],'support':r['support'],'rng_draw':None,
         'evicted_id':None,'admitted':False,'incoming_discarded':False}
  if policy=='present':entry['incoming_discarded']=True
  elif len(kept)<cap:kept.append(r);entry['admitted']=True
  else:
   index=None
   if policy=='fifo':index=0
   elif policy=='reservoir':
    index=rng.randrange(r['id']);entry['rng_draw']={'population_size':r['id'],'inclusive_lower':0,'exclusive_upper':r['id'],'draw':index}
   elif policy=='diversity':
    nine=kept+[r];vectors=np.stack([x['descriptor'] for x in nine]);diff=vectors[:,None,:]-vectors[None,:,:]
    dist=np.mean(diff[:,:,:11]**2,axis=2)+np.mean(diff[:,:,11:]**2,axis=2)
    scores=[]
    for omitted in range(9):
     ids=[j for j in range(9) if j!=omitted]
     scores.append(min(float(dist[a,b]) for a in ids for b in ids if a<b))
    entry['diversity_removal_scores']=scores
    index=min((j for j,x in enumerate(scores) if x==max(scores)),key=lambda j:(nine[j]['id'],nine[j]['hash']))
   else:raise ValueError('unpressured reference exceeded declared record cap')
   if index>=8:entry['incoming_discarded']=True
   else:
    entry['evicted_id']=kept[index]['id'];entry['admitted']=True;replacements+=1
    if policy=='fifo':kept.pop(index);kept.append(r)
    else:kept[index]=r
  rejections+=int(entry['incoming_discarded'])
  out[r['id']]={'completion':entry,'ids':[x['id'] for x in kept],'replacements':replacements,'rejections':rejections}
 return out


def join_packets(messages):
 events=[];right=[]
 for m in messages:
  for e,lc,rc in zip(m['events'],m['event_left_clipped'],m['event_right_clipped']):
   if events and right[-1] and lc and events[-1][1]==e[0] and events[-1][2]==e[2]:events[-1][1]=float(e[1]);right[-1]=rc
   else:events.append(list(e));right.append(rc)
 return events


def pitch(events,t):
 for on,off,p in events:
  if on<=t<off:return int(p)
 return 128


def witness(c,raw,events,times,labels):
 """Check each saved transform witness, never search for other candidates."""
 scale=c['scale'];shift=c['shift'];offset=c['offset'];qs=raw['query_support']
 demand(.65-1e-10<=scale<=1.5+1e-10 and shift in range(-5,6),'candidate transform outside frozen range')
 demand(close([c['start']*scale+offset,c['end']*scale+offset],qs),'candidate endpoints do not map to query support')
 demand(abs(c['center']-(c['start']+c['end'])/2)<1e-9,'candidate center arithmetic')
 demand(c['query_rows_skipped']==0 and c['query_runs_skipped']==0 and c['contradictions']==0,'candidate skipped/contradicted observations')
 demand(c['continuous_exact_support_verified'] is True,'missing exact-support witness')
 demand(c['verified_query_rows']==raw['query_row_ids'] and c['query_rows_verified']==len(raw['query_row_ids']),'candidate query row ledger')
 # Partition query support at every query edge and every mapped history edge.
 # Check open segment interiors; endpoint identities follow the explicit saved
 # boundary brackets rather than unstable floating-point inverse evaluation.
 edges=[qs[0],qs[1]]
 for on,off,p in events:
  edges.extend(x for x in (on,off,scale*on+offset,scale*off+offset) if qs[0]<x<qs[1])
 edges=sorted(edges);merged=[]
 for x in edges:
  if not merged or x-merged[-1]>1e-9:merged.append(x)
 for a,b in zip(merged,merged[1:]):
  if b-a<=1e-9:continue
  qt=(a+b)/2;hp=pitch(events,(qt-offset)/scale);qp=pitch(events,qt)
  demand(qp==(hp if hp==128 else hp+shift),'continuous midpoint pitch contradiction')
 for b in c['boundary_witnesses']:
  q=b['query_boundary'];h=b['history_boundary']
  demand(abs(q-(scale*h+offset))<=1e-8,'boundary transform contradiction')
  for x,bracket in ((q,b['query_bracket']),(h,b['history_bracket'])):
   demand(bracket[0]-1e-8<=x<=bracket[1]+1e-8,'boundary outside recorded bracket')
 for pair in c['correspondence']:
  hp,qp=pair['history_pitch'],pair['query_pitch']
  demand(qp==(hp if hp==128 else hp+shift),'run pitch contradiction')
 # Independently verify saved query/history sample rows using the explicit
 # query boundary sequence to avoid inversion roundoff at exact transitions.
 boundaries=np.asarray([b['query_boundary'] for b in c['boundary_witnesses']])
 runp=np.asarray([p['query_pitch'] for p in c['correspondence']])
 qids=np.asarray(raw['query_row_ids'],dtype=int)
 demand(np.array_equal(runp[np.searchsorted(boundaries,times[qids],side='right')],labels[qids]),'saved query-row witness contradiction')
 hids=np.asarray(c['verified_history_rows'],dtype=int)
 origins=c['constraint_coordinate_origins'];local=c['local_representative']
 demand(close([scale,offset],[local[0],origins['query']+local[1]-local[0]*origins['history']]),'local/global transform coordinates')
 allhistory=np.asarray(raw['history_row_ids'],dtype=int)
 hs=c['history_support'];component=allhistory[(times[allhistory]>=hs[0])&(times[allhistory]<=hs[1])]
 mapped=scale*(times[component]-origins['history'])+local[1]+origins['query']
 expected_history=component[(mapped>=qs[0])&(mapped<=qs[1])]
 demand(np.array_equal(hids,expected_history),'incomplete verified history-row ledger')
 if len(hids):
  actual=np.where(labels[hids]==128,128,labels[hids]+shift)
  mapped_checked=scale*(times[hids]-origins['history'])+local[1]+origins['query']
  predicted=runp[np.searchsorted(boundaries,mapped_checked,side='right')]
  demand(np.array_equal(actual,predicted),'saved history-row witness contradiction')
 demand(c['history_rows_verified']==len(hids),'history-row count')


def validate_one(folder,session,obs,records,packets,ledger,policy,mode):
 required=['started.json','ready.json','arrivals.jsonl.gz','response.json','completed.json','stderr.txt']
 for name in required:demand((folder/name).exists(),'missing '+name)
 demand(not (folder/'failure.json').exists(),'recorded worker failure')
 started=read(folder/'started.json');ready=read(folder/'ready.json');done=read(folder/'completed.json');response=read(folder/'response.json')
 demand(started['input_sha256']==session['observations_sha256'],'started input hash')
 demand(started['policy']==policy and started['removed']==(mode=='removed'),'started routing')
 demand(ready['ready'] and ready['guard'] and ready['policy']==policy and ready['seed']==SEED,'ready guard/seed')
 demand(done['response_sha256']==sha(folder/'response.json') and done['arrivals_sha256']==sha(folder/'arrivals.jsonl.gz'),'completion output hash')
 demand(done['exit_code']==0 and done['labels_read_by_worker'] is False and done['replay'] is False,'completion execution flags')
 cap=512 if policy=='unpressured' else 8;bytecap=8*1024*1024 if policy=='unpressured' else 256*1024
 ids=[];replacements=rejections=0;count=0;last_received=-math.inf;maxbytes=0
 with gzip.open(folder/'arrivals.jsonl.gz','rt') as log:
  for count,line in enumerate(log,1):
   demand(count<=len(packets),'extra arrival receipt');expected=packets[count-1];u=count-1;saved=json.loads(line);r=saved['receipt']
   demand(saved['packet_sha256']==expected['packet_hash'],'packet hash at unit '+str(u))
   demand(r['type']=='arrival' and r['unit']==u and r['available_at']==u+1,'arrival chronology')
   demand(r['unit_events_sha256']==expected['event_hash'],'arrival clipped event hash')
   demand(r['received_monotonic']>=last_received,'nonmonotone receipt');last_received=r['received_monotonic']
   demand(r['recent_units']==list(range(max(0,u-3),u+1)),'recent ring retained beyond four units')
   demand(r['recent_evicted_units']==([u-4] if u>=4 else []),'destructive eviction ledger')
   demand(r['recent_evictions']==max(0,u-3),'recent eviction counter')
   if expected['completion'] is None:demand(r['completion'] is None,'unexpected completed record')
   else:
    want=ledger[expected['completion']['id']];entry=r['completion']
    demand(set(entry)==set(want['completion']),'completion fields')
    for k,v in want['completion'].items():
     demand(close(entry[k],v,1e-15) if k=='diversity_removal_scores' else entry[k]==v,'completion ledger '+k)
    ids=want['ids'];replacements=want['replacements'];rejections=want['rejections']
   demand(r['retained_ids']==ids and len(ids)<=cap,'retained ID ledger/capacity')
   demand(r['persistent_replacements']==replacements and r['admission_rejections']==rejections,'policy counters')
   demand(r['persistent_capacity']==cap and r['persistent_byte_cap']==bytecap,'declared capacity')
   demand(0<r['persistent_bytes']<=bytecap,'persistent byte cap');maxbytes=max(maxbytes,r['persistent_bytes'])
 demand(count==len(packets),'incomplete arrival ledger')
 removed=[i for i in ids if records[i-1]['support'][0]<obs['occurrences'][0]['support'][1] and obs['occurrences'][0]['support'][0]<records[i-1]['support'][1]] if mode=='removed' else []
 ids=[i for i in ids if i not in removed]
 demand(response['removed_record_ids']==removed and response['source_removed']==(mode=='removed'),'source removal ledger')
 demand([r['id'] for r in response['retained_records']]==ids,'final retained IDs')
 for r in response['retained_records']:
  wanted=records[r['id']-1]
  demand(r['support']==wanted['support'] and r['events']==wanted['events'],'retained event values/support differ from arrivals')
  demand(r['hash']==wanted['hash'] and r['events_sha256']==wanted['hash'],'retained event hash')
  demand(r['available_at']==wanted['available_at'],'record availability')
  demand(close(r['descriptor'],wanted['descriptor'],0),'retained descriptor')
 demand(response['persistent_replacements']==replacements and response['replacements']==replacements and response['admission_rejections']==rejections,'final policy counters')
 if policy in POLICIES[:3]:demand(replacements>=12,'fewer than12 actual replacements')
 demand(0<response['persistent_bytes']<=response['peak_persistent_bytes']<=bytecap and response['peak_persistent_bytes']>=maxbytes,'final/peak byte cap')
 final=len(packets);recent=list(range(final-4,final));demand(response['recent_units']==recent,'final ring units')
 demand(all(u>=obs['occurrences'][0]['support'][1] for u in recent),'source survives recent ring')
 recentmessages=[packets[u]['message'] for u in recent];recent_events=join_packets(recentmessages)
 demand(response['ring_events_sha256']==digest(recent_events,[[u,u+1] for u in recent]),'final ring hash')
 units=set(recent)
 for i in ids:units.update(range(*records[i-1]['support']))
 ordered=sorted(units);events=join_packets([packets[u]['message'] for u in ordered]);segments=[]
 for u in ordered:
  if segments and segments[-1][1]==u:segments[-1][1]=u+1
  else:segments.append([u,u+1])
 demand(response['input_events_sha256']==digest(events,segments),'rebuilt matcher evidence hash')
 if mode=='removed':demand(1 not in ids and all(not (a<3 and b>0) for a,b,p in events),'source-derived events/cache survive removal')
 demand(response['simulation_observations_available_at']==final,'final simulated availability')
 demand(last_received<=response['prediction_finished_monotonic']<=response['output_ready_monotonic']<=response['broker_received_monotonic'],'output predates arrived evidence or broker receipt')
 demand(abs(response['output_available_at']-(final+response['processing_seconds']))<1e-8,'full processing availability arithmetic')
 demand(response['output_available_at']>=response['simulation_compute_only_finish']>=final,'simulated availability ordering')
 demand(response['simulated_delivery_available_at']>=final,'broker simulated delivery ordering')
 raw=response['raw'];demand(raw['method']=='G-exact-score' and raw['query_rows_skipped']==0 and raw['contradictions']==0,'raw G exact/no-skip flags')
 candidates=raw['candidates'];demand(len(candidates)==raw['candidate_count'],'raw candidate count')
 demand(raw['accepted']==(len(candidates)==1),'frozen unique-window acceptance')
 demand(raw['selected']==(candidates[0] if len(candidates)==1 else None),'selected candidate serialization')
 times=np.concatenate([u+np.arange(10)*.1+.05 for u in ordered]);unitids=np.repeat(ordered,10);labels=np.array([pitch(events,t) for t in times])
 loud=np.flatnonzero(labels!=128);end=times[loud[-1]];qids=np.flatnonzero((times>end-2+1e-8)&(times<=end+1e-8))
 demand(raw['query_row_ids']==qids.tolist() and close(raw['query_support'],[times[qids[0]],times[qids[-1]]]),'query selection from arrived evidence')
 demand(raw['history_row_ids']==np.flatnonzero(unitids<unitids[qids[0]]).tolist(),'history row availability')
 mappings=[]
 for j,c in enumerate(candidates):
  witness(c,raw,events,times,labels)
  containing=[i for i in ids if records[i-1]['support'][0]<=c['start'] and c['end']<=records[i-1]['support'][1]]
  intersecting=[i for i in ids if records[i-1]['support'][0]<c['end'] and c['start']<records[i-1]['support'][1]]
  mappings.append({'candidate_index':j,'containing_record_ids':containing,'intersecting_record_ids':intersecting})
  if mode=='removed':demand(not (0<=c['center']<3),'candidate centered in removed source support')
 demand(response['candidate_record_mappings']==mappings,'candidate record mapping')
 demand(response['compatible_record_ids']==sorted({i for x in mappings for i in x['containing_record_ids']}),'compatible record set')
 expected_selected=mappings[0]['containing_record_ids'][0] if len(mappings)==1 and len(mappings[0]['containing_record_ids'])==1 else None
 demand(response['selected_record_id']==expected_selected,'selected record ID')
 return {'arrivals':count,'replacements':replacements,'retained_records':len(ids),'candidate_witnesses_checked':len(candidates),'peak_persistent_bytes':response['peak_persistent_bytes'],'source_absent_recent':True}


def main():
 ap=argparse.ArgumentParser();ap.add_argument('split',choices=EXPECTED);args=ap.parse_args();start=time.monotonic()
 errors=[];checked=[];expected_paths=set();manifest=read(ROOT/'input-manifest.json')['sessions']
 sessions=[s for s in manifest if s['split']==args.split]
 for s in sessions:
  try:
   path=ROOT/s['path'];demand(sha(path/'observations.json')==s['observations_sha256'],'input hash');demand(sha(path/'labels.json')==s['labels_sha256'],'label hash')
   obs=read(path/'observations.json');records,packets=input_evidence(obs)
  except Exception as exc:errors.append({'session':s['session_id'],'error':repr(exc)});continue
  for policy in POLICIES:
   try:ledger=policy_ledger(records,policy)
   except Exception as exc:errors.append({'session':s['session_id'],'policy':policy,'error':'policy audit: '+repr(exc)});continue
   for mode in (['full'] if s['cell']=='foil' else ['full','removed']):
    folder=ROOT/'outputs'/args.split/s['session_id']/policy/mode;rel=str(folder.relative_to(ROOT));expected_paths.add(rel)
    try:summary=validate_one(folder,s,obs,records,packets,ledger,policy,mode);checked.append({'path':rel,**summary})
    except Exception as exc:errors.append({'path':rel,'error':repr(exc)})
 actual={str(p.parent.relative_to(ROOT)) for p in (ROOT/'outputs'/args.split).rglob('completed.json')}
 if len(expected_paths)!=EXPECTED[args.split]:errors.append({'error':'wrong expected readout cardinality','actual':len(expected_paths),'expected':EXPECTED[args.split]})
 if actual!=expected_paths:errors.append({'error':'completed path set mismatch','missing':sorted(expected_paths-actual),'unexpected':sorted(actual-expected_paths)})
 complete=ROOT/(args.split+'-completed.json')
 if not complete.exists():errors.append({'error':'missing split completion receipt'})
 elif read(complete).get('completed_readouts')!=EXPECTED[args.split]:errors.append({'error':'split completion count'})
 result={'split':args.split,'passed':not errors and len(checked)==EXPECTED[args.split],'errors':errors,'readouts':len(checked),
         'expected_readouts':EXPECTED[args.split],'completed_artifacts':len(actual),'checks':checked,'elapsed_seconds':time.monotonic()-start,
         'candidate_calls':0,'qualification_replays':0,'validation_scope':'Saved evidence and mathematical policy/witness audit, no candidate search or execution; frozen guarded worker source remains necessary to assess absence of hidden accesses.'}
 out=ROOT/('validation-'+args.split+'.json');out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
 raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
