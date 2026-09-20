"""Choose one boundary configuration from saved development records only."""
from pathlib import Path
import json,numpy as np
from events import event_metrics
HERE=Path(__file__).resolve().parent
def main():
    d=HERE/'data/development';truth={t['episode']:t for t in map(json.loads,(d/'truth.jsonl').read_text().splitlines())};cache=list(map(json.loads,(d/'cache.jsonl').read_text().splitlines()));cfg=json.loads((HERE/'initial_model.json').read_text());rows=[]
    for q in cfg['boundary_grid']:
        grouped={}
        for x in cache:
            t=truth[x['episode']];m=event_metrics(x['operational']['events'][q['id']],t['bounds'],t['reset_sample']);grouped.setdefault(t['group'],[]).append(m)
        row={'id':q['id']}
        for metric in ['f1','pitch_accuracy','split_rate','merge_rate']:row[metric]=float(np.mean([np.mean([m[metric] for m in ms]) for ms in grouped.values()]))
        rows.append(row)
    best=min(rows,key=lambda r:(-r['f1'],-r['pitch_accuracy'],r['split_rate']+r['merge_rate'],r['id']));cfg['selected']=best['id'];cfg['development_grid']=False
    (HERE/'frozen_model.json').write_text(json.dumps(cfg,indent=2));(HERE/'development_selection.json').write_text(json.dumps({'grid':rows,'selected':best,'rule':'max F1, max pitch accuracy, min split+merge, lexicographic ID'},indent=2));print(json.dumps(best))
if __name__=='__main__':main()
