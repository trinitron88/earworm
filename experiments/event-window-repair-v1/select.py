"""Finite support-policy selection on saved development data, no audio rerun."""
from pathlib import Path
import json,numpy as np
from events import event_metrics
from records import read_lines
from scoring import measure
HERE=Path(__file__).resolve().parent
def main():
    d=HERE/'data/development';truth={r['episode']:r for r in map(json.loads,read_lines(d/'truth.jsonl.gz'))};cache=list(map(json.loads,read_lines(d/'cache.jsonl.gz')));cfg=json.loads((HERE/'initial_model.json').read_text());rows=[]
    for policy in cfg['support_grid']:
        by={}
        for x in cache:
            t=truth[x['episode']];v=by.setdefault(t['group'],{'pitch':[],'available':[],'prediction':[]});m=event_metrics(x['operational']['events'][policy['id']],t['bounds'],t['reset_sample']);v['pitch'].append(m['pitch_accuracy']);v['available'].append(m['pitch_availability'])
            if t['condition']=='intact':v['prediction'].append(measure(x['operational']['forecasts'][policy['id']]['reference'],t)['accuracy'])
        r={'id':policy['id'],'trim_samples':policy['trim_samples']}
        for metric in ['pitch','available','prediction']:r[metric]=float(np.mean([np.mean(v[metric]) for v in by.values()]))
        r['feasible']=r['available']>=.80;rows.append(r)
    feasible=[r for r in rows if r['feasible']];best=min(feasible,key=lambda r:(-r['pitch'],-r['prediction'],r['trim_samples'])) if feasible else None
    (HERE/'development_selection.json').write_text(json.dumps({'grid':rows,'selected':best,'objective':'feasible availability>=.80; max group pitch accuracy, max intact prediction accuracy, smallest trim','no_other_policy_family':True},indent=2));print(json.dumps({'selected':best,'grid':rows}))
    if best:
        cfg['selected_support']=best['id'];cfg['support_development']=False;(HERE/'frozen_model.json').write_text(json.dumps(cfg,indent=2))
if __name__=='__main__':main()
