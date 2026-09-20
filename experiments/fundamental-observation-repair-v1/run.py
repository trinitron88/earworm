"""Evaluator and arrival broker. One pass per split; future stays outside worker."""
import argparse, base64, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from collections import Counter
import numpy as np
from stimuli import group, CELLS, CONDITIONS
from scoring import measure,safe

HERE=Path(__file__).resolve().parent

def canonical(x):return json.dumps(safe(x),sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(x).hexdigest()
def filehash(p):return digest(p.read_bytes())
def code_hash():return digest(canonical({p.name:filehash(p) for p in sorted(HERE.glob('*.py'))}).encode())

class Log:
    def __init__(self,path):self.f=path.open('x');self.seq=0;self.prev='0'*64
    def add(self,kind,body,sync=False):
        self.seq+=1
        rec={'seq':self.seq,'monotonic_ns':time.monotonic_ns(),'utc_ns':time.time_ns(),'kind':kind,'previous_sha256':self.prev,**body}
        payload=canonical(rec); self.prev=digest(payload.encode()); self.f.write(canonical({'record':rec,'sha256':self.prev})+'\n')
        if sync:self.f.flush();os.fsync(self.f.fileno())
        return self.seq
    def close(self):self.f.flush();os.fsync(self.f.fileno());self.f.close()

class Arrival:
    def __init__(self,config,log):
        self.p=subprocess.Popen([sys.executable,'-B',str(HERE/'worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
        self.config=config;self.log=log
    def rpc(self,msg):
        text=canonical(msg);self.p.stdin.write(text+'\n');self.p.stdin.flush();line=self.p.stdout.readline()
        if not line:raise RuntimeError('Predictor process failed')
        return json.loads(line),line.rstrip('\n')
    def init(self):return self.rpc({'op':'init','config':self.config})[0]
    def arrive(self,raw):return self.rpc({'op':'arrive','samples_b64':base64.b64encode(raw).decode()})[0]
    def predict(self):return self.rpc({'op':'forecast'})
    def reset(self):return self.rpc({'op':'reset'})[0]
    def close(self):self.p.stdin.close();assert self.p.wait(timeout=20)==0


def run(split,config_path):
    start=time.monotonic();out=HERE/'data'/split;out.mkdir(parents=True,exist_ok=True)
    marker=out/'STARTED.json'
    if marker.exists():raise RuntimeError('Split already started. Preserve it; no duplicate evaluation.')
    manifest=json.loads((HERE/'split_manifest.json').read_text());entries=[x for x in manifest['groups'] if x['split']==split]
    prior_seconds=sum(json.loads(p.read_text())['elapsed_seconds'] for p in (HERE/'data').glob('*/runtime.json'))
    if split=='heldout':
        frozen=json.loads((HERE/'freeze.json').read_text());receipt=json.loads((HERE/'preregistration_receipt.json').read_text())
        assert receipt['comment_id'] and receipt['protocol_sha256']==frozen['files']['protocol.json']
        for name,h in frozen['files'].items():assert filehash(HERE/name)==h,name
        assert code_hash()==frozen['execution_code_sha256']
    cfg=json.loads(config_path.read_text());ch=code_hash();mh=filehash(config_path)
    revision=subprocess.check_output(['git','-C',str(HERE),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(HERE),'status','--porcelain'],text=True).strip()
    inputs_match_commit=None
    if split=='heldout':
        for name,h in frozen['files'].items():
            blob=subprocess.check_output(['git','-C',str(HERE),'show','HEAD:experiments/fundamental-observation-repair-v1/'+name])
            assert digest(blob)==h,name
        inputs_match_commit=True
    (out/'execution_sources.json').write_text(json.dumps({f.name:f.read_text() for f in sorted(HERE.glob('*.py'))},indent=2)+'\n')
    (out/'config_used.json').write_text(json.dumps(cfg,indent=2)+'\n')
    ledger=HERE/'run_ledger.json'
    ledger_data=json.loads(ledger.read_text()) if ledger.exists() else []
    allocation=len(entries)*22
    assert sum(x['allocated_streams'] for x in ledger_data)+allocation<=880
    ledger_data.append({'split':split,'allocated_streams':allocation,'started_ns':time.time_ns()})
    ledger.write_text(json.dumps(ledger_data,indent=2))
    marker.write_text(canonical({'split':split,'start_utc_ns':time.time_ns(),'execution_revision':revision,'dirty_at_start':bool(dirty),'dirty_paths_at_start':dirty.splitlines(),'execution_inputs_match_commit':inputs_match_commit,'execution_code_sha256':ch,'model_sha256':mh})+'\n')
    log=Log(out/'events.jsonl');arrival=Arrival(cfg,log)
    caches=(out/'arrived_cache.jsonl').open('x');truthfile=(out/'truth.jsonl').open('x');recipes=[];balance=[];invariance=[];episode_count=0
    try:
        for entry in entries:
            episodes,recipe=group(entry);recipes.append({'group_id':entry['group_id'],**recipe})
            for family in CELLS:
                for condition in (CONDITIONS if family=='joint' else ['intact']):
                    pair=[x for x in episodes if x['family']==family and x['condition']==condition]
                    a,b=pair
                    assert Counter(map(digest,a['blocks']))==Counter(map(digest,b['blocks']))
                    assert a['blocks'][-5:]==b['blocks'][-5:]
                    assert sorted(a['underlying_pitches'],key=str)==sorted(b['underlying_pitches'],key=str)
                    balance.append({'group_id':entry['group_id'],'family':family,'condition':condition,'identical_multiset':True,'identical_final_two_history_and_probe':True,'blocks_per_prefix':14,'duration_s':sum(len(x)/64000 for x in a['blocks'])})
            for ep in episodes:
                if time.monotonic()-start+prior_seconds>7200:raise RuntimeError('Two-hour local compute bound reached')
                eid=f"{ep['group_id']}/{ep['family']}/{ep['condition']}/{ep['variant']}"
                status=arrival.init();assert status['guard_probe_blocked'] and status['capacity']==32
                log.add('episode_start',{'episode':eid,'worker_ready':status,'model_sha256':mh,'execution_code_sha256':ch})
                observations=[];memory=[];prefix_hashes=[]
                for i,raw in enumerate(ep['blocks']):
                    if ep['reset_before_index']==i:
                        reset=arrival.reset();memory=[];log.add('deliberate_reset',{'episode':eid,'before_arrival':i,'state':reset})
                    response=arrival.arrive(raw);obs=response['observation'];observations.append(obs);memory.append(obs);prefix_hashes.append(digest(raw))
                    assert response['evictions']==0 and response['occupancy']<=32
                    log.add('arrival',{'episode':eid,'arrival_index':i,'input_fields':['op','samples_b64'],'sample_sha256':digest(raw),'observation':obs,'occupancy':response['occupancy'],'evictions':0})
                pred,pred_bytes=arrival.predict()
                assert pred['prefix_sha256']==digest(canonical(prefix_hashes).encode()) and pred['arrivals']==14 and pred['evictions']==0
                forecast_seq=log.add('forecast_commit',{'episode':eid,'forecast_bytes_sha256':digest(pred_bytes.encode()),'payload':pred,'model_sha256':mh,'execution_code_sha256':ch},sync=True)
                # Change the evaluator's withheld future without crossing the arrival API.
                if ep['condition']=='intact' and ep['variant']==0:
                    held_future=ep['alternative_future'];again,again_bytes=arrival.predict()
                    assert held_future!=ep['future'] and again_bytes==pred_bytes
                    invariance.append({'episode':eid,'first_future_sha256':digest(ep['future']),'substituted_future_sha256':digest(held_future),'same_forecast_bytes':True,'forecast_sha256':digest(pred_bytes.encode())})
                    log.add('future_invariance',{'episode':eid,**invariance[-1]},sync=True)
                log.add('reveal',{'episode':eid,'forecast_sequence':forecast_seq,'future_sha256':digest(ep['future'])},sync=True)
                future_observation=arrival.arrive(ep['future'])['observation']
                log.add('revealed_observation',{'episode':eid,'observation':future_observation})
                truth={**ep['truth'],'episode':eid,'group_id':ep['group_id'],'split':split,'family':ep['family'],'condition':ep['condition'],'variant':ep['variant'],'future_sha256':digest(ep['future']),'prefix_wave_sha256':prefix_hashes,'prefix_true_pitches':ep['underlying_pitches'],'target_never_in_prefix':digest(ep['future']) not in prefix_hashes,'diagnostic_order':ep['diagnostic_order'],'reset_before_index':ep['reset_before_index']}
                truthfile.write(canonical(truth)+'\n')
                caches.write(canonical({'episode':eid,'observations':observations,'memory_at_forecast':memory,'forecast':pred,'future_observation':future_observation})+'\n')
                scoring={name:measure(f,truth) for name,f in pred['forecasts'].items()}
                log.add('score',{'episode':eid,'scores':scoring},sync=True);episode_count+=1
        arrival.close();log.close();caches.close();truthfile.close()
        for name,value in [('recipes.json',recipes),('balance.json',balance),('future_invariance.json',invariance)]:
            (out/name).write_text(json.dumps(value,indent=2)+'\n')
        runtime={'split':split,'episodes':episode_count,'additional_future_invariance_probes':len(invariance),'elapsed_seconds':time.monotonic()-start,'prior_elapsed_seconds':prior_seconds,'execution_revision':revision,'dirty_at_start':bool(dirty),'dirty_paths_at_start':dirty.splitlines(),'execution_inputs_match_commit':inputs_match_commit,'execution_code_sha256':ch,'model_sha256':mh,'python':sys.version.split()[0],'numpy':np.__version__,'end_utc_ns':time.time_ns()}
        assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) < 2*1024**3
        (out/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n');print(json.dumps(runtime))
    except BaseException:
        caches.flush();truthfile.flush();log.f.flush();arrival.p.terminate();raise

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('split',choices=['development','calibration','heldout']);ap.add_argument('--config',type=Path,required=True);a=ap.parse_args();run(a.split,a.config)
