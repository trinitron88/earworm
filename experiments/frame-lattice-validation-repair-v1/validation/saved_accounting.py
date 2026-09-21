"""Post-run accounting of saved records; no audio/model execution."""
from pathlib import Path
import gzip,json,sys
P=Path(__file__).resolve().parent.parent
split=sys.argv[1];d=P/'data'/split
maxima={k:0 for k in ['raw_buffer_bytes','serialized_listener_payload_bytes','serialized_config_bytes','lattice_frames','comparator_frames','events_per_front','candidate_alignments','serialized_candidate_scratch_bytes','feature_audio_availability_s','feature_dispatch_to_computation_s','forecast_dispatch_to_commit_s','chunks','evictions']}
frames=0;episodes=0;searches=0
for x in map(json.loads,gzip.open(d/'cache.jsonl.gz','rt')):
 p=x['operational'];episodes+=1
 vals={'raw_buffer_bytes':p['raw_buffer_samples']*4,'serialized_listener_payload_bytes':len(json.dumps(p,sort_keys=True,separators=(',',':')).encode()),'lattice_frames':max(map(len,p['lattice'].values())),'comparator_frames':len(p['frames']),'events_per_front':max(map(len,p['events'].values())),'chunks':p['chunk_count'],'evictions':p['evictions']}
 for k,v in vals.items():maxima[k]=max(maxima[k],v)
 for seq in p['lattice'].values():
  frames+=len(seq)
  for z in seq:maxima['feature_audio_availability_s']=max(maxima['feature_audio_availability_s'],(z['available_sample']-z['end_sample'])/16000)
 for fs in p['forecasts'].values():
  for f in fs.values():
   if 'search_candidate_count' in f:
    searches+=1;maxima['candidate_alignments']=max(maxima['candidate_alignments'],f['search_candidate_count']);maxima['serialized_candidate_scratch_bytes']=max(maxima['serialized_candidate_scratch_bytes'],f['search_serialized_candidate_bytes'])
dispatch={};forecast={}
for z in map(json.loads,gzip.open(d/'events.jsonl.gz','rt')):
 r=z['record'];eid=r['episode']
 if r['kind']=='chunk_dispatch':dispatch[eid,r['offset']]=r['monotonic_ns']
 elif r['kind']=='forecast_dispatch':forecast[eid]=r['monotonic_ns']
 elif r['kind']=='forecast_commit':
  maxima['forecast_dispatch_to_commit_s']=max(maxima['forecast_dispatch_to_commit_s'],(r['monotonic_ns']-forecast[eid])/1e9)
  for fs in r['payload']['lattice'].values():
   for f in fs:
    offset=(f['available_sample']//1024-1)*1024
    maxima['feature_dispatch_to_computation_s']=max(maxima['feature_dispatch_to_computation_s'],(f['computed_monotonic_ns']-dispatch[eid,offset])/1e9)
maxima['serialized_config_bytes']=len(json.dumps(json.loads((d/'config_used.json').read_text()),sort_keys=True,separators=(',',':')).encode())
result={'split':split,'episodes':episodes,'retained_lattice_frames':frames,'search_readouts':searches,'maxima':maxima,'accounting_scope':'Raw PCM, complete serialized frame/event/forecast/hash payload, config, and transient alignment candidates counted separately. Event-front internal pending references, counters and runtime/Python object overhead are bounded by source but not measured as heap/RSS. Shared measurements may be counted multiple times by serialization. Archives are evaluator-only and not memory. No eviction occurred; no long-term retention conclusion.'}
(P/'validation'/f'accounting_{split}.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
