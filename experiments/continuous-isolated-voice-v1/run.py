"""Arrival broker/evaluator; single execution per split; true bounds outside worker."""
import json,hashlib,subprocess,sys,base64,time,os
from pathlib import Path
from collections import Counter
import numpy as np
from stimuli import group,CELLS,CONDITIONS
from scoring import safe,measure
from model import observation,predict
HERE=Path(__file__).resolve().parent

def canonical(x):return json.dumps(safe(x),sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x).hexdigest()
def codehash():return digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(HERE.glob('*.py'))}).encode())
class Log:
    def __init__(self,path):self.f=path.open('x');self.prev='0'*64;self.seq=0
    def add(self,kind,body,sync=False):
        self.seq+=1;r={'seq':self.seq,'kind':kind,'previous_sha256':self.prev,'utc_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),**body};self.prev=digest(canonical(r).encode());self.f.write(canonical({'record':r,'sha256':self.prev})+'\n')
        if sync:self.f.flush();os.fsync(self.f.fileno())
        return self.seq
    def close(self):self.f.flush();os.fsync(self.f.fileno());self.f.close()
class Worker:
    def __init__(self):self.p=subprocess.Popen([sys.executable,'-B',str(HERE/'worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
    def rpc(self,m):
        self.p.stdin.write(canonical(m)+'\n');self.p.stdin.flush();s=self.p.stdout.readline()
        if not s:raise RuntimeError('Worker failed')
        return json.loads(s),s.rstrip('\n')
    def close(self):self.p.stdin.close();assert self.p.wait(timeout=20)==0

def run(split,config):
    start=time.monotonic();d=HERE/'data'/split;d.mkdir(parents=True,exist_ok=True)
    assert not (d/'STARTED.json').exists(),'Do not repeat started split'
    cfg=json.loads(config.read_text());groups=[g for g in json.loads((HERE/'split_manifest.json').read_text())['groups'] if g['split']==split];mh=digest(config.read_bytes());ch=codehash();sha=subprocess.check_output(['git','-C',str(HERE),'rev-parse','HEAD'],text=True).strip()
    if split=='heldout':
        freeze=json.loads((HERE/'freeze.json').read_text());receipt=json.loads((HERE/'preregistration_receipt.json').read_text());assert receipt['protocol_sha256']==freeze['files']['protocol.json'] and receipt['comment_id']
        assert ch==freeze['execution_code_sha256']
        for n,h in freeze['files'].items():
            assert digest((HERE/n).read_bytes())==h;assert digest(subprocess.check_output(['git','-C',str(HERE),'show','HEAD:experiments/continuous-isolated-voice-v1/'+n]))==h
    ledger=HERE/'run_ledger.json';counts=json.loads(ledger.read_text()) if ledger.exists() else [];assert sum(x['allocated_streams'] for x in counts)+len(groups)*22<=880;counts.append(dict(split=split,allocated_streams=len(groups)*22,start_utc_ns=time.time_ns()));ledger.write_text(json.dumps(counts,indent=2))
    dirty=subprocess.check_output(['git','-C',str(HERE),'status','--porcelain'],text=True).strip();(d/'STARTED.json').write_text(canonical(dict(start_utc_ns=time.time_ns(),execution_revision=sha,execution_code_sha256=ch,model_sha256=mh,frozen_inputs_match_commit=split=='heldout',dirty_paths=dirty.splitlines())))
    (d/'config_used.json').write_text(json.dumps(cfg,indent=2));(d/'execution_sources.json').write_text(json.dumps({p.name:p.read_text() for p in HERE.glob('*.py')},indent=2))
    log=Log(d/'events.jsonl');worker=Worker();cache=(d/'cache.jsonl').open('x');waves=(d/'wave_archive.jsonl').open('x');truthfile=(d/'truth.jsonl').open('x');recipes=[];balance=[];invariance=[];nep=0
    try:
      for g in groups:
        episodes,recipe=group(g);recipes.append(recipe)
        for cell in CELLS:
          for cond in (CONDITIONS if cell=='joint' else ['intact']):
            a,b=[e for e in episodes if e['cell']==cell and e['condition']==cond]
            assert Counter(t['wave_sha256'] for t in a['bounds'])==Counter(t['wave_sha256'] for t in b['bounds'])
            assert len(a['prefix'])==len(b['prefix']) and a['prefix'][a['probe_start']*4:]==b['prefix'][b['probe_start']*4:]
            balance.append(dict(group=g['group_id'],cell=cell,condition=cond,source_unit_byte_multiset=True,probe_and_tail_identical=True,samples=len(a['prefix'])//4,chunks=len(a['prefix'])//4096,boundary_on_chunk_fraction=sum(t['start']%1024==0 for t in a['bounds'][1:-1])/len(a['bounds'][1:-1])))
        for e in episodes:
            assert time.monotonic()-start+sum(json.loads(q.read_text())['elapsed_seconds'] for q in (HERE/'data').glob('*/runtime.json'))<7200
            eid=f"{e['group']}/{e['cell']}/{e['condition']}/{e['variant']}";ready,_=worker.rpc({'op':'init','config':cfg});assert ready['guard_probe_blocked'];log.add('start',dict(episode=eid,ready=ready,code_sha256=ch,model_sha256=mh));n=len(e['prefix'])//4
            for offset in range(0,n,1024):
                if e['reset_sample']==offset:
                    reset,_=worker.rpc({'op':'reset'});log.add('reset',dict(episode=eid,response=reset))
                raw=e['prefix'][offset*4:(offset+1024)*4];log.add('chunk_dispatch',dict(episode=eid,offset=offset));response,_=worker.rpc({'op':'arrive','samples_b64':base64.b64encode(raw).decode()});log.add('arrival',dict(episode=eid,offset=offset,wave_sha256=digest(raw),input_fields=['op','samples_b64'],response=response))
            pred,pbytes=worker.rpc({'op':'forecast'});assert pred['evictions']==0 and pred['chunk_count']<=32
            commit=log.add('forecast_commit',dict(episode=eid,payload=pred,forecast_sha256=digest(pbytes.encode()),model_sha256=mh),True)
            if e['condition']=='intact' and e['variant']==0:
                withheld=e['alternative_future'];again,abytes=worker.rpc({'op':'forecast'});assert abytes==pbytes and withheld!=e['future'];v=dict(episode=eid,same_forecast_bytes=True,forecast_sha256=digest(pbytes.encode()),first_future_sha256=digest(e['future']),other_future_sha256=digest(withheld));invariance.append(v);log.add('future_invariance',v,True)
            # Ceiling receives boundaries only in evaluator, after real forecasts commit.
            oracle=[]
            for t in e['bounds'][:-1]:
                if e['reset_sample'] is not None and t['end']<=e['reset_sample']:continue
                lo=max(t['start'],e['reset_sample'] or 0);obs=observation(e['prefix'][lo*4:t['end']*4],cfg)
                if t['pitch'] is None:obs={**obs,'unmasked_observation':obs,'pitch_semitones':None,'pitch_available':False,'pitch_hz':None}
                oracle.append(dict(start_sample=lo,end_sample=t['end'],available_sample=((t['end']+1023)//1024)*1024,state_pitch=t['pitch'],observation=obs))
            ceiling=predict(oracle,cfg);log.add('oracle_boundary_forecast_commit',dict(episode=eid,forecasts=ceiling,diagnostic_only=True),True)
            log.add('reveal',dict(episode=eid,forecast_sequence=commit,future_sha256=digest(e['future'])),True)
            futureobs=observation(e['future'],cfg);log.add('revealed_observation',dict(episode=eid,observation=futureobs))
            t={**e['truth'],'episode':eid,'group':e['group'],'cell':e['cell'],'condition':e['condition'],'variant':e['variant'],'bounds':e['bounds'],'reset_sample':e['reset_sample'],'probe_start':e['probe_start'],'probe_end':e['probe_end'],'arrived_samples':n,'family':g['family']}
            outputs={**pred['forecasts'],'oracle-boundary':ceiling};scores={front:{name:measure(f,t) for name,f in fs.items()} for front,fs in outputs.items()};log.add('score',dict(episode=eid,scores=scores),True)
            truthfile.write(canonical(t)+'\n');cache.write(canonical(dict(episode=eid,operational=pred,oracle_events=oracle,oracle_forecasts=ceiling,future_observation=futureobs))+'\n');waves.write(canonical(dict(episode=eid,prefix_b64=base64.b64encode(e['prefix']).decode(),future_b64=base64.b64encode(e['future']).decode()))+'\n');nep+=1
      worker.close();log.close();cache.close();waves.close();truthfile.close()
      for name,val in [('recipes.json',recipes),('balance.json',balance),('future_invariance.json',invariance)]: (d/name).write_text(json.dumps(val,indent=2))
      size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());assert size<2*1024**3
      runtime=dict(split=split,episodes=nep,additional_future_probes=len(invariance),elapsed_seconds=time.monotonic()-start,execution_revision=sha,execution_code_sha256=ch,model_sha256=mh,retained_bytes=size,python=sys.version,numpy=np.__version__,end_utc_ns=time.time_ns());(d/'runtime.json').write_text(json.dumps(runtime,indent=2));print(json.dumps(runtime))
    except BaseException:
      log.f.flush();cache.flush();waves.flush();truthfile.flush();worker.p.terminate();raise
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('split',choices=['development','calibration','heldout']);ap.add_argument('--config',type=Path,required=True);a=ap.parse_args();run(a.split,a.config)
