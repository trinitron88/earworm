"""Saved-file provenance only; never imports or runs the listener."""
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent.parent
root=P.parent.parent
old=P.parent/'frame-lattice-init-repair-v1'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((P/'reused_evidence.json').read_text())['files']
checked=[]
for n,d in manifest.items():
 assert h(old/n)==d
 if n not in ['verify.py','run_ledger.json']:
  assert h(P/n)==d;checked.append(n)
prior=json.loads((P/'prior_artifact_hashes.json').read_text())
assert all(h(root/n)==d for n,d in prior.items())
assert (P/'run.py').read_bytes()==(old/'run.py').read_bytes()
assert (P/'worker.py').read_bytes()==(old/'worker.py').read_bytes()
assert not (old/'data/heldout').exists()
assert sum(x['allocated_streams'] for x in json.loads((P/'run_ledger.json').read_text()))<=960
out={'all_pass':True,'reused_byte_identical_files':checked,'historical_files':len(prior),'scientific_and_runtime_sources_unchanged':True,'old_heldout_unstarted':True,'new_heldout_started':(P/'data/heldout/STARTED.json').exists(),'old_validator_sha256':h(old/'verify.py'),'corrected_validator_sha256':h(P/'verify.py')}
(P/'validation/preservation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='reused_byte_identical_files'}))
