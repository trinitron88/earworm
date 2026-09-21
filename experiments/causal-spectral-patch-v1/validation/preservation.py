"""File/commit identity checks only; never runs the frozen failed report."""
from pathlib import Path
import json,hashlib,subprocess
P=Path(__file__).resolve().parent.parent;R=P.parent.parent
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((P/'prior_artifact_hashes.json').read_text());assert all(h(R/n)==v for n,v in prior.items())
initial=json.loads((P/'development_freeze.json').read_text())['files'];assert all(h(P/n)==v for n,v in initial.items())
freeze=json.loads((P/'freeze.json').read_text());sha='d7586c0ca6667806bd99c859f83a1feee722649c'
for n,v in freeze['files'].items():assert h(P/n)==v and hashlib.sha256(subprocess.check_output(['git','-C',str(R),'show',sha+':experiments/causal-spectral-patch-v1/'+n])).hexdigest()==v
assert sum(x['allocated_streams'] for x in json.loads((P/'run_ledger.json').read_text()))==960
assert "truth[f'{g}/joint/ambiguous/{v}']" in (P/'analyze.py').read_text()
assert not (P/'results/heldout/controls.json').exists() and not (P/'results/heldout/comparisons.csv').exists() and not (P/'results/heldout/safety.json').exists()
assert json.loads((P/'results/heldout/decision.json').read_text())['branch']=='invalid'
result={'all_pass':True,'historical_files':len(prior),'development_frozen_files':len(initial),'heldout_frozen_files':len(freeze['files']),'execution_revision':sha,'failed_analyzer_unchanged':True,'streams':960,'no_missing_result_fabrication':True}
(P/'validation/preservation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
