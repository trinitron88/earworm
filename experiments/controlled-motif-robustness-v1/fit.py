"""Readout-only selection from already-arrived development/calibration caches."""
import json,itertools,copy,math
from pathlib import Path
import numpy as np
import reference_model as ref
HERE=Path(__file__).resolve().parent
def records(split):
    truth={x['episode']:x for x in map(json.loads,(HERE/'data'/split/'truth.jsonl').read_text().splitlines())}
    return [(x,truth[x['episode']]) for x in map(json.loads,(HERE/'data'/split/'arrived_cache.jsonl').read_text().splitlines())]
def score(rows,name,cfg):
    correct=[];loss=[]
    for x,t in rows:
        h=x['memory_at_forecast'];anchor=h[-1]['pitch_semitones'];p=ref.distribution(ref.candidates(h,name,cfg),name,cfg,anchor)
        k=int(np.argmax(p));point=None if k==49 or anchor is None else anchor+k-24
        correct.append(point is not None and abs(point-t['pitch_semitones'])<=.35)
        ys=[]
        for v,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):
            absolute=t['prefix_true_pitches'][-1]+v
            offset=None if anchor is None else absolute-anchor
            k=49 if offset is None or not -24.5<offset<24.5 else int(round(offset))+24
            ys.append((k,mass))
        loss.append(sum(-mass*math.log(p[k]) if p[k]>0 else math.inf for k,mass in ys))
    return float(np.mean(correct)),float(np.mean(loss))
def fit(stage):
    cfg=json.loads((HERE/('initial_model.json' if stage=='development' else 'development_model.json')).read_text());new=cfg['new'];rows=records(stage);report=[]
    names=['present','recency','transition','retrieval_absolute','retrieval_transposed']
    if stage=='development':
        prior=np.zeros(50)
        for x,t in rows:
            for v,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):prior[int(v)+24]+=mass
        new['prior']=(prior/prior.sum()).tolist()
        for name in names[1:]:
            trials=[]
            orders=[1,2,3] if name=='transition' else [1 if name=='recency' else 3]
            for order,cut in itertools.product(orders,[.1,.3,.7]):
                candidate=copy.deepcopy(new);candidate[name+'_order']=order;candidate[name+'_cutoff']=cut
                accuracy,loss=score(rows,name,candidate);trials.append(dict(order=order,cutoff=cut,accuracy=accuracy,log_loss=loss))
            best=min(trials,key=lambda t:(-t['accuracy'],t['log_loss'],t['order'],t['cutoff']))
            new[name+'_order']=best['order'];new[name+'_cutoff']=best['cutoff'];report.append(dict(model=name,grid=trials,selected=best))
        output='development_model.json'
    else:
        for name in names:
            trials=[]
            for temp,sigma,floor in itertools.product([.05,.2],[.08,.2],[.001,.05]):
                candidate=copy.deepcopy(new);cal=dict(temperature=temp,sigma=sigma,floor=floor);candidate['calibration'][name]=cal
                accuracy,loss=score(rows,name,candidate);trials.append(dict(parameters=cal,accuracy=accuracy,log_loss=loss))
            best=min(trials,key=lambda t:(t['log_loss'],t['parameters']['temperature'],t['parameters']['sigma'],t['parameters']['floor']))
            new['calibration'][name]=best['parameters'];report.append(dict(model=name,grid=trials,selected=best))
        output='frozen_model.json'
    assert cfg['reference']==json.loads((HERE/'reference_config.json').read_text())
    (HERE/output).write_text(json.dumps(cfg,indent=2)+'\n');(HERE/(stage+'_selection.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'stage':stage,'selected':[dict(model=x['model'],selected=x['selected']) for x in report]}))
if __name__=='__main__':
    import sys
    assert sys.argv[1] in ['development','calibration'];fit(sys.argv[1])
