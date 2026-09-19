"""Development hyperparameters and calibration-only probability parameters."""
import argparse,itertools,json,math
from pathlib import Path
import numpy as np
from model import NAMES,candidates,distribution
HERE=Path(__file__).resolve().parent

def load(split):
    p=HERE/'data'/split
    cache=[json.loads(x) for x in (p/'arrived_cache.jsonl').read_text().splitlines()]
    truth={x['episode']:x for x in map(json.loads,(p/'truth.jsonl').read_text().splitlines())}
    return [(c,truth[c['episode']]) for c in cache]

def target(t):
    y=np.zeros(50)
    for interval,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):y[int(round(interval))+24]+=mass
    return y

def loss(rows,name,cfg):
    total=0.
    for c,t in rows:
        h=c['memory_at_forecast'];a=candidates(h,name,cfg);p=distribution(a,name,cfg,h[-1]['pitch_semitones']);total-=float(sum(target(t)*np.log(p)))
    return total/len(rows)

def main(stage):
    if stage=='development':
        rows=load('development');cfg=json.loads((HERE/'initial_model.json').read_text());prior=np.zeros(50)
        for c,t in rows:prior+=target(t)
        cfg['prior']=(prior/prior.sum()).tolist();search={}
        selected=[(c,t) for c,t in rows if t['condition'] in ['intact','ambiguous']]
        for name,orders in [('transition',[1,2,3]),('retrieval_absolute',[2,3,4]),('retrieval_transposed',[2,3,4]),('relational',[2,3])]:
            results=[]
            for order,cutoff in itertools.product(orders,[.1,.3,.6]):
                candidate=dict(cfg);candidate[name+'_order']=order;candidate[name+'_cutoff']=cutoff
                results.append({'order':order,'cutoff':cutoff,'development_log_loss':loss(selected,name,candidate)})
            best=min(results,key=lambda r:(r['development_log_loss'],r['order'],r['cutoff']))
            cfg[name+'_order']=best['order'];cfg[name+'_cutoff']=best['cutoff'];search[name]=results
        path=HERE/'development_model.json';assert not path.exists();path.write_text(json.dumps(cfg,indent=2)+'\n')
        (HERE/'development_selection.json').write_text(json.dumps(search,indent=2)+'\n')
    else:
        rows=load('calibration');cfg=json.loads((HERE/'development_model.json').read_text());cfg['calibration']={};search={}
        # Calibration chooses probabilities only; structure/order/gates remain development-selected.
        for name in NAMES:
            cached=[(candidates(c['memory_at_forecast'],name,cfg),c['memory_at_forecast'][-1]['pitch_semitones'],target(t)) for c,t in rows]
            results=[]
            for temperature,sigma,floor in itertools.product([.05,.2,.5],[.08,.2,.4],[.001,.01,.05]):
                parameters=dict(temperature=temperature,sigma=sigma,floor=floor);candidate={**cfg,'calibration':{name:parameters}}
                value=float(np.mean([-sum(y*np.log(distribution(a,name,candidate,anchor))) for a,anchor,y in cached]))
                results.append({**parameters,'calibration_log_loss':value})
            best=min(results,key=lambda r:(r['calibration_log_loss'],r['temperature'],r['sigma'],r['floor']))
            cfg['calibration'][name]={k:best[k] for k in ['temperature','sigma','floor']};search[name]=results
        path=HERE/'frozen_model.json';assert not path.exists();path.write_text(json.dumps(cfg,indent=2)+'\n')
        (HERE/'calibration_selection.json').write_text(json.dumps(search,indent=2)+'\n')
    print(json.dumps({'stage':stage,'model':cfg},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['development','calibration']);main(p.parse_args().stage)
