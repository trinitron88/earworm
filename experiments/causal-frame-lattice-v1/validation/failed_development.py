"""Saved-only validation of the failed attempt; does not invoke worker/audio code."""
from pathlib import Path
import json,gzip,hashlib,subprocess
P=Path(__file__).resolve().parent.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
start=json.loads((P/'data/development/STARTED.json').read_text());previous='0'*64;records=[]
for line in gzip.open(P/'data/development/events.jsonl.gz','rt'):
 x=json.loads(line);r=x['record'];assert r['previous_sha256']==previous and r['seq']==len(records)+1;assert sha(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode())==x['sha256'];previous=x['sha256'];records.append(r)
assert records[-1]['kind']=='forecast_dispatch'
assert not any(r['kind'] in ['forecast_commit','oracle_boundary_forecast_commit','reveal','score'] for r in records)
assert not (P/'data/calibration').exists() and not (P/'data/heldout').exists()
for name in ['cache','truth','wave_archive']:
 assert gzip.open(P/f'data/development/{name}.jsonl.gz','rt').read()==''
source=json.loads((P/'data/development/execution_sources.json').read_text());hashes={n:sha(s.encode()) for n,s in source.items()};assert sha(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode())==start['execution_code_sha256']
for n,s in source.items():
 assert (P/n).read_text()==s
 committed=subprocess.check_output(['git','-C',str(P),'show',start['execution_revision']+':experiments/causal-frame-lattice-v1/'+n]);assert committed==s.encode()
old=json.loads((P/'prior_artifact_hashes.json').read_text());assert all(sha((P.parent.parent/n).read_bytes())==h for n,h in old.items())
arrivals=[r for r in records if r['kind']=='arrival'];assert len({r['episode'] for r in records})==1
result={'saved_failure_evidence_passes':True,'scientific_validity_passed':False,'records':len(records),'arrived_chunks':len(arrivals),'arrived_samples':arrivals[-1]['response']['arrived_samples'],'completed_forecasts':0,'reveals':0,'completed_episodes':0,'started_streams':1,'allocated_development_budget':200,'calibration_started':False,'heldout_started':False,'source_matches_attempted_execution':True,'historical_files_unchanged':len(old),'last_record_sha256':previous,'unavailable_due_to_failure':['forecast outputs','source/transform/prediction metrics','worker final extraction counters','full waveform archive','save/restore and future-invariance results'],'note':'No runtime.json was written. Do not treat failure-evidence verification as scientific validation. No extraction or rerun performed.'};(P/'validation/failure.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
