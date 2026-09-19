"""Check the audit against its saved outputs and the frozen calibration routine."""
import argparse, ast, hashlib, importlib.util, json, platform, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--record',type=Path,required=True);a=ap.parse_args()
    base=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('saved_audit',base/'analyze_saved_evidence.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    with tempfile.TemporaryDirectory(prefix='earworm-audit-check-') as tmp:
        output=Path(tmp)/'results'
        subprocess.run([sys.executable,'-B',str(base/'analyze_saved_evidence.py'),'--root',str(a.root),'--out',str(output)],check=True,stdout=subprocess.DEVNULL)
        comparisons=[]
        for p in sorted((base/'results').iterdir()):
            assert p.read_bytes()==(output/p.name).read_bytes(),p.name
            comparisons.append({'file':p.name,'identical':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    config=json.loads((a.root/'work/accounts_results/frozen_config.json').read_text())
    manifest=json.loads((a.root/'work/accounts_stimuli/manifest.json').read_text())
    raw=[json.loads(l) for l in (base/'candidate_evidence.jsonl').read_text().splitlines()]
    cal=[r for r in raw if r['split']=='calibration']
    # Compile only these two pure functions; execute no imports, model fit, or runner.
    tree=ast.parse((a.root/'work/accounts_experiment.py').read_text())
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('histories','threshold_fit')]
    assert len(funcs)==2
    ns={'np':np,'value':lambda row,method,cfg:audit.support(row['evidence'],cfg)}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'frozen_threshold_arithmetic','exec'),ns)
    groups=[g for g in manifest['groups'] if g['split']=='calibration']
    queries=[b for b in manifest['blocks'] if b['role']=='query' and b['split']=='calibration' and b['phase']=='core']
    table={q['query_id']:{rid:{'evidence':ev} for rid,ev in q['candidates'].items()} for q in cal}
    expected=json.loads((base/'results/calibration_sensitivity.json').read_text());checks=[]
    for omitted in [None]+[g['id'] for g in groups]:
        gs=[g for g in groups if g['id']!=omitted];qs=[q for q in queries if q['group_id']!=omitted]
        result=ns['threshold_fit'](gs,qs,table,'accounts',config)
        target=expected['full_calibration_reproduced'] if omitted is None else next(f['retained_calibration'] for f in expected['folds'] if f['omitted_group']==omitted)
        assert result['threshold']==target['threshold'] and result['correct_singletons']==target['correct_singletons'] and result['false_acceptances']==target['absent_false_acceptances']
        checks.append({'omitted_group':omitted,'exact_frozen_threshold_routine_match':True})
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'numpy':np.__version__,
            'clean_audit_reexecution':comparisons,'frozen_threshold_routine_comparisons':checks,
            'note':'Audit calculations only. Original experiment pipelines, alignment, audio generation, training, and replay were not run.'}
    a.record.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__': main()
