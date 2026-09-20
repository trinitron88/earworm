"""Finite development-only selection, no new audio execution."""
import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def main():
    d=HERE/'data/development';truth={x['episode']:x for x in map(json.loads,(d/'truth.jsonl').read_text().splitlines())};cache=list(map(json.loads,(d/'arrived_cache.jsonl').read_text().splitlines()));cfg=json.loads((HERE/'initial_model.json').read_text());rows=[]
    for threshold in cfg['adapter']['threshold_grid']:
        bygroup={}
        for x in cache:
            t=truth[x['episode']];v=bygroup.setdefault(t['group_id'],[])
            for obs,p in zip(x['observations'],t['prefix_true_pitches']):
                if p is None:continue
                q=obs['repaired_observation']['finite_grid_observations'][str(threshold)]['pitch_semitones'];v.append((q is not None and abs(q-p)<=.35,abs(q-p) if q is not None else 100.))
        rows.append(dict(threshold=threshold,group_weighted_pitch_accuracy=float(np.mean([np.mean([z[0] for z in vals]) for vals in bygroup.values()])),group_weighted_absolute_error=float(np.mean([np.mean([z[1] for z in vals]) for vals in bygroup.values()]))))
    best=min(rows,key=lambda x:(-x['group_weighted_pitch_accuracy'],x['group_weighted_absolute_error'],x['threshold']));cfg['adapter']['periodicity_threshold']=best['threshold']
    (HERE/'frozen_model.json').write_text(json.dumps(cfg,indent=2)+'\n');(HERE/'development_selection.json').write_text(json.dumps({'grid':rows,'selected':best,'ties':'accuracy descending, error ascending, threshold ascending','no_primary_retrieval_parameters_changed':True},indent=2)+'\n');print(json.dumps(best))
if __name__=='__main__':main()
