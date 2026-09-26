"""Evaluator broker. One isolated, label-blind worker process per charged readout."""
import argparse, datetime, gzip, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
POLICIES=['fifo','reservoir','diversity','unpressured','present']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def units(obs):
    records=obs['occurrences']+[obs['query']]
    ends={int(math.ceil(r['support'][1]-1e-10)):[int(math.floor(r['support'][0]+1e-10)),int(math.ceil(r['support'][1]-1e-10))] for r in records}
    events=[e for r in records for e in r['events']]
    final=int(math.ceil(records[-1]['support'][1]-1e-10))
    for u in range(final):
        selected=[e for e in events if e[1]>u and e[0]<u+1]
        yield {'op':'unit','unit':u,'available_at':u+1,
               'events':[[max(e[0],u),min(e[1],u+1),e[2]] for e in selected],
               'event_left_clipped':[e[0]<u for e in selected],
               'event_right_clipped':[e[1]>u+1 for e in selected],
               'completed_support':ends.get(u+1)}
def total_started():return len(list((ROOT/'outputs').rglob('started.json')))+len(list((ROOT/'qualification').rglob('started.json')))
def budget_check(reserve=0):
    stage=json.loads((ROOT/'stage.json').read_text()); active=stage['active_intervals'][-1]
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(active['start'])).total_seconds()
    used=stage['prior_prelimit_conservative_seconds']+stage.get('helper_conservative_seconds',0)+elapsed
    if used+reserve>7200:raise RuntimeError('aggregate resource reserve exhausted')
    if total_started()>=900:raise RuntimeError('900-call cap')
    return used

def execute(obs, dest, policy, removed=False, input_hash=None):
    dest.mkdir(parents=True,exist_ok=True)
    if (dest/'completed.json').exists():return {'skipped_completed':True}
    if (dest/'started.json').exists():raise RuntimeError('started readout cannot be replayed: '+str(dest.relative_to(ROOT)))
    used=budget_check(reserve=300)
    with (dest/'started.json').open('x') as f:
        json.dump({'started_at':now(),'policy':policy,'removed':removed,'input_sha256':input_hash,'aggregate_seconds_before':used,'call_number':total_started()},f,indent=2)
    started=time.monotonic(); process=None
    try:
        env=dict(os.environ);env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        with (dest/'stderr.txt').open('w') as err:
            process=subprocess.Popen([sys.executable,str(ROOT/'worker.py'),policy,'--seed','202609260701'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1,env=env,cwd=ROOT)
            def read():
                line=process.stdout.readline()
                if not line:raise RuntimeError('worker ended without expected receipt; see stderr')
                return json.loads(line)
            ready=read();save(dest/'ready.json',ready)
            if not ready.get('ready'):raise RuntimeError('worker not ready')
            with gzip.open(dest/'arrivals.jsonl.gz','wt') as log:
                for msg in units(obs):
                    process.stdin.write(json.dumps(msg,separators=(',',':'))+'\n');process.stdin.flush()
                    receipt=read()
                    log.write(json.dumps({'packet_sha256':hashlib.sha256(json.dumps(msg,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'receipt':receipt},separators=(',',':'))+'\n')
                    if receipt.get('error'):raise RuntimeError(str(receipt['error']))
            cmd={'op':'predict','remove_support':obs['occurrences'][0]['support'] if removed else None}
            process.stdin.write(json.dumps(cmd)+'\n');process.stdin.flush()
            response=read()
            # Persist raw prediction before any label file is read/scored.
            save(dest/'response.json',response)
            process.stdin.close();code=process.wait(timeout=60)
            if code!=0 or response.get('error'):raise RuntimeError('worker failure, exit='+str(code))
        done={'completed_at':now(),'elapsed_seconds':time.monotonic()-started,'response_sha256':sha(dest/'response.json'),'arrivals_sha256':sha(dest/'arrivals.jsonl.gz'),'exit_code':0,'labels_read_by_worker':False,'replay':False}
        save(dest/'completed.json',done);return done
    except BaseException as e:
        if process is not None and process.poll() is None:process.terminate();process.wait(timeout=10)
        save(dest/'failure.json',{'at':now(),'error':repr(e),'elapsed_seconds':time.monotonic()-started,'no_replay':True})
        raise

def main():
    ap=argparse.ArgumentParser();ap.add_argument('split',choices=['development','calibration','evaluation']);args=ap.parse_args()
    if args.split=='evaluation':
        receipt=json.loads((ROOT/'preregistration_receipt.json').read_text())
        assert receipt['execution_sha'] and receipt['comment_url']
        frozen=json.loads((ROOT/'freeze.json').read_text())['files']
        for p,digest in frozen.items():assert sha(ROOT/p)==digest,p
    manifest=json.loads((ROOT/'input-manifest.json').read_text())
    sessions=[s for s in manifest['sessions'] if s['split']==args.split]
    expected={'development':140,'calibration':140,'evaluation':560}[args.split]
    planned=sum(5*(1 if s['cell']=='foil' else 2) for s in sessions)
    assert planned==expected
    for s in sessions:
        fp=ROOT/s['path']/'observations.json';assert sha(fp)==s['observations_sha256']
        obs=json.loads(fp.read_text())
        for policy in POLICIES:
            for mode in (['full'] if s['cell']=='foil' else ['full','removed']):
                path=ROOT/'outputs'/args.split/s['session_id']/policy/mode
                execute(obs,path,policy,mode=='removed',s['observations_sha256'])
                print(json.dumps({'session':s['session_id'],'policy':policy,'mode':mode,'completed':True}),flush=True)
    save(ROOT/(args.split+'-completed.json'),{'at':now(),'completed_readouts':expected,'stage':args.split,'total_calls_so_far':total_started()})
if __name__=='__main__':main()
