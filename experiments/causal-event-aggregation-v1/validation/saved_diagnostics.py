"""Declared resource/family/uncertainty summaries from saved outputs only."""
import json,csv,gzip,math
from pathlib import Path
from collections import defaultdict
P=Path(__file__).resolve().parent.parent;out=P/'results/heldout'
def write(n,x):(out/n).write_text(json.dumps(x,indent=2)+'\n')
meta={g['group_id']:g for g in json.loads((P/'split_manifest.json').read_text())['groups']};gr=list(csv.DictReader((out/'groups.csv').open()));families=[]
for model in sorted({r['model'] for r in gr}):
 for family in ['pure','fundamental','overtone']:
  rs=[r for r in gr if r['model']==model and r['condition']=='intact' and meta[r['group']]['family']==family];families.append({'model':model,'family':family,'groups':len({r['group'] for r in rs}),'accuracy':sum(float(r['accuracy']) for r in rs)/len(rs),'oracle_accuracy_loss':1-sum(float(r['accuracy']) for r in rs)/len(rs)})
write('all_model_families.json',families)
dispatch={};dur=[]
for line in gzip.open(P/'data/heldout/events.jsonl.gz','rt'):
 r=json.loads(line)['record']
 if r['kind']=='chunk_dispatch':dispatch[(r['episode'],r['offset'])]=r['monotonic_ns']
 elif r['kind']=='arrival':dur.append((r['monotonic_ns']-dispatch[(r['episode'],r['offset'])])/1e9)
late=[];window_durations=[];hypotheses=[];unknown=[];calls=0;cfg=json.loads((P/'frozen_model.json').read_text())
for line in gzip.open(P/'data/heldout/cache.jsonl.gz','rt'):
 x=json.loads(line);pred=x['operational'];hypotheses.append(pred['forecasts'][cfg['selected_aggregation']+'_mixture']['reference']['history_paths'])
 for e in pred['events'][cfg['selected_aggregation']]:
  orig=pred['events'][cfg['selected']][e['original_event_index']];late.append((e['computed_monotonic_ns']-orig['computed_monotonic_ns'])/1e9);window_durations.extend((w['end_sample']-w['start_sample'])/16000 for w in e['windows'])
  if e['state_pitch'] is not None:unknown.append(e['distribution']['unknown_mass'])
rt=[json.loads((P/'data'/s/'runtime.json').read_text()) for s in ['development','calibration','heldout']];v=json.loads((P/'validation/heldout.json').read_text());dev=json.loads((P/'validation/development.json').read_text())
resources={'total_streams':880,'episodes':sum(r['episodes'] for r in rt),'additional_future_probes':sum(r['additional_future_probes'] for r in rt),'window_extractions':sum(r['aggregation_window_calls'] for r in rt),'trim16_support_extractions':sum(r['support_observation_calls'] for r in rt),'acoustic_split_seconds':sum(r['elapsed_seconds'] for r in rt),'max_chunk_dispatch_response_seconds':max(dur),'mean_chunk_dispatch_response_seconds':sum(dur)/len(dur),'max_original_to_aggregate_seconds':max(late),'max_history_paths_retained':max(hypotheses),'mean_pitched_event_unknown_mass_pooled':sum(unknown)/len(unknown),'maximum_chunks':v['maximum_chunks'],'maximum_raw_bytes':v['maximum_raw_prefix_bytes'],'maximum_heldout_serialized_listener_bytes':v['maximum_serialized_listener_payload_bytes'],'maximum_development_serialized_listener_bytes':dev['maximum_serialized_listener_payload_bytes'],'paid_compute':0,'memory_note':'All accessible event/window/alternative-front records included in serialized payload, plus raw buffer separately. Not heap/RSS. Shared MAP/mixture records counted twice conservatively. Evaluator archive inaccessible.'}
write('resources.json',resources);print(json.dumps(resources))
