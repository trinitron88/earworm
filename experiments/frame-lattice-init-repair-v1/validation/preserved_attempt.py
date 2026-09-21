"""Read-only failure/provenance validation; no audio extraction or worker run."""
from pathlib import Path
import json,hashlib,gzip
P=Path(__file__).resolve().parent.parent;old=P.parent/'causal-frame-lattice-v1';sha=lambda b:hashlib.sha256(b).hexdigest()
fixed=json.loads((P/'scientific_source_hashes.json').read_text())
for n,h in fixed.items():assert sha((P/n).read_bytes())==h and (P/n).read_bytes()==(old/n).read_bytes()
worker=(P/'worker.py').read_text();original=(old/'worker.py').read_text();assert worker[worker.index('blocked=[]'):]==original[original.index('blocked=[]'):]
added='# Initialize the exact numerical helper before the unchanged audit hook.\nnp.median(np.array([0.,1.,2.]))\nnp.median(np.array([0.,1.]))\n';assert worker.replace(added,'')==original
pre=json.loads((P/'preflight_result.json').read_text());assert pre['all_pass'] and pre['same_forecast_bytes'] and pre['guard_events']==['open','open'];assert all(sha((P/n).read_bytes())==h for n,h in pre['source_hashes'].items())
prior=json.loads((P/'prior_artifact_hashes.json').read_text());assert all(sha((P.parent.parent/n).read_bytes())==h for n,h in prior.items())
assert not (P/'data/heldout').exists();assert json.loads((P/'validation/calibration.json').read_text())['all_pass'] is False
counts={}
for split in ['development','calibration']:
 last='0'*64;n=0;kind={}
 for line in gzip.open(P/'data'/split/'events.jsonl.gz','rt'):
  v=json.loads(line);r=v['record'];n+=1;assert r['seq']==n and r['previous_sha256']==last and sha(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode())==v['sha256'];last=v['sha256'];kind[r['kind']]=kind.get(r['kind'],0)+1
 counts[split]={'records':n,'record_kinds':kind,'last_sha256':last}
 assert kind['forecast_commit']==160 and kind['reveal']==160 and kind['save_restore']==8 and kind['future_invariance']==32
result={'failure_evidence_passes':True,'scientific_validity_passed':False,'scientific_files_unchanged':len(fixed),'historical_files_unchanged':len(prior),'guard_and_worker_loop_unchanged':True,'preflight_passed':True,'chains':counts,'heldout_started':False,'calibration_integrity_failure_retained':True,'no_acoustic_or_worker_calls':True};(P/'validation/preserved_attempt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
