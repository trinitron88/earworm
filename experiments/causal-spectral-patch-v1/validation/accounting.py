"""Saved-only predictor state and timing accounting, without listener execution."""
from pathlib import Path
import sys,json
P=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(P));from records import read_lines
S=sys.argv[1];d=P/'data'/S;cfg=json.loads((d/'config_used.json').read_text());mx={k:0 for k in ['raw_buffer_bytes','serialized_output_bytes','patch_frames','patch_channel_frames','candidate_alignments','reported_search_array_bytes','forecast_dispatch_commit_s','frame_dispatch_computation_s','frame_audio_availability_s','saved_full_state_bytes','chunks','evictions']};episodes=0;channels=0;patch_calls=0
for x in map(json.loads,read_lines(d/'cache.jsonl.gz')):
 p=x['operational'];episodes+=1;vals={'raw_buffer_bytes':p['raw_buffer_samples']*4,'serialized_output_bytes':len(json.dumps(p,sort_keys=True,separators=(',',':')).encode()),'patch_frames':len(p['patch_frames']),'patch_channel_frames':sum(len(f['channels']) for f in p['patch_frames']),'chunks':p['chunk_count'],'evictions':p['evictions']};channels+=vals['patch_channel_frames']
 for k,v in vals.items():mx[k]=max(mx[k],v)
 for fs in p['patch_forecasts'].values():
  patch_calls+=2
  for name in ['reference','absolute']:
   f=fs[name];mx['candidate_alignments']=max(mx['candidate_alignments'],f['search_candidate_count']);mx['reported_search_array_bytes']=max(mx['reported_search_array_bytes'],f['search_scratch_array_bytes'])
 for f in p['patch_frames']:mx['frame_audio_availability_s']=max(mx['frame_audio_availability_s'],(f['available_sample']-f['end_sample'])/16000)
fd={};cd={};transactions=0
for z in map(json.loads,read_lines(d/'events.jsonl.gz')):
 r=z['record'];eid=r['episode']
 if r['kind']=='chunk_dispatch':cd[eid,r['offset']]=r['monotonic_ns']
 elif r['kind']=='forecast_dispatch':fd[eid]=r['monotonic_ns']
 elif r['kind']=='forecast_commit':
  mx['forecast_dispatch_commit_s']=max(mx['forecast_dispatch_commit_s'],(r['monotonic_ns']-fd[eid])/1e9)
  for f in r['payload']['patch_frames']:mx['frame_dispatch_computation_s']=max(mx['frame_dispatch_computation_s'],(f['computed_monotonic_ns']-cd[eid,(f['available_sample']//1024-1)*1024])/1e9)
 elif r['kind']=='save_restore':mx['saved_full_state_bytes']=max(mx['saved_full_state_bytes'],r['serialized_state_bytes'])
 elif r['kind']=='silence_missing_probe':transactions+=1
out={'episodes':episodes,'retained_channel_frames':channels,'patch_search_readouts':patch_calls,'silence_missing_transactions':transactions,'maxima':mx,'fixed_filter_matrix_bytes':135*2049*8,'serialized_configuration_bytes':len(json.dumps(cfg,separators=(',',':')).encode()),'temporary_array_conservative_upper_bytes':4*mx['reported_search_array_bytes'],'candidate_scalar_record_upper_bytes':cfg['patch_max_candidates']*2048,'accounting_note':'Reported search arrays omit temporary products; conservative4x upper covers arrays and reductions, plus up to5000 scalar candidate records at2048 serialized bytes each. Full pickle snapshots include raw,all comparator/patch state,filter matrix,config,cache,status,counters at one existing probe/group. Snapshot maximum is across those probes, not every process instant. Serialized output counts duplicated shared references; not heap/RSS. Evaluation archives inaccessible; zero eviction.'}
(P/'validation'/f'accounting_{S}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
