"""Single-use bounded evaluator. Children receive observations, never evaluator labels."""
import argparse, datetime, hashlib, json, math, os, pathlib, select, subprocess, sys, time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def loadnp(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def blob(d):
    import base64,io
    b=io.BytesIO();np.savez_compressed(b,**d);return base64.b64encode(b.getvalue()).decode()
def packet(rows,events,u,exact):
    mask=rows['unit']==u;r={k:rows[k][mask].copy() for k in ['t','unit','rms','clean','available_at']}
    if exact:
        hit=(events[:,0]<u+1)&(events[:,1]>u);e=events[hit].copy()
        r['event_left_clipped']=e[:,0]<u;r['event_right_clipped']=e[:,1]>u+1
        e[:,0]=np.maximum(e[:,0],u);e[:,1]=np.minimum(e[:,1],u+1);r['events']=e
    return r
def read_line(proc,timeout=60):
    end=time.monotonic()+timeout;buffer=b''
    while b'\n' not in buffer:
        remain=end-time.monotonic()
        if remain<=0 or not select.select([proc.stdout],[],[],max(0,remain))[0]:raise TimeoutError('Bounded worker response deadline exceeded')
        chunk=os.read(proc.stdout.fileno(),1048576)
        if not chunk:raise RuntimeError('Worker ended without response')
        buffer+=chunk
    assert buffer.endswith(b'\n') and buffer.count(b'\n')==1
    return json.loads(buffer)
def communicate(proc,cmd):
    proc.stdin.write(json.dumps(cmd)+'\n');proc.stdin.flush()
    return read_line(proc)
def one_readout(rows,events,method,mode,remove_units,out):
    assert not out.exists(),'Never replay an exposed readout'
    out.mkdir(parents=True)
    write(out/'started.json',{'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':method,'mode':mode})
    proc=subprocess.Popen([sys.executable,str(ROOT/'engine.py'),method],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    began=time.monotonic();arrival=[]
    try:
        ready=read_line(proc);assert ready['guard']
        for u in np.unique(rows['unit']):
            arrival.append(communicate(proc,{'op':'arrive','blob':blob(packet(rows,events,int(u),method=='G-exact'))}))
        requested=time.monotonic()
        answer=communicate(proc,{'op':'predict','mode':mode,'remove_units':remove_units if mode=='removed' else []})
        received=time.monotonic()
        answer['parent_response_received_monotonic']=received
        answer['parent_prediction_request_monotonic']=requested
        answer['actual_output_availability_upper_bound']=received
        answer['readout_roundtrip_seconds']=received-requested
        answer['simulated_output_availability_upper_bound']=answer['simulation_observations_available_at']+(received-requested)
        # Durable raw response is committed before outcome scoring.
        write(out/'response.json',answer);write(out/'arrivals.json',arrival)
        proc.stdin.close();proc.wait(timeout=30);err=proc.stderr.read()
        if proc.returncode:raise RuntimeError(err[-4000:])
        write(out/'completed.json',{'wall_seconds':time.monotonic()-began,'returncode':proc.returncode,'stderr':err})
        return answer
    except BaseException:
        proc.kill();proc.wait();raise

def readout_count():
    probes=ROOT/'qualification/ledger.json'
    pn=len(json.loads(probes.read_text())['calls']) if probes.exists() else 0
    return pn+len(list((ROOT/'outputs').glob('**/started.json')))

def resource_guard(reserve=600):
    stage=json.loads((ROOT/'stage.json').read_text())
    started=datetime.datetime.fromisoformat(stage['preparation_started_at'])
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()
    # 1800 sec explicitly reserved for independently running helpers/preparation.
    if elapsed+1800+reserve>7200:raise RuntimeError('Aggregate conservative time budget requires checkpoint')
    if readout_count()>=400:raise RuntimeError('Readout budget exhausted')
    n=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    if n>512*1024**2:raise RuntimeError('New-artifact budget exceeded')
    return {'elapsed_wall_seconds':elapsed,'parallel_preparation_reserve_seconds':1800,'new_artifact_bytes':n,'charged_readouts':readout_count()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--panel',action='store_true');parser.add_argument('--diagnostics',action='store_true');args=parser.parse_args()
    assert (ROOT/'preregistration_receipt.json').exists(),'Require published preregistration'
    freeze=json.loads((ROOT/'freeze.json').read_text())
    for rel,sha in freeze['files'].items():assert digest(ROOT/rel)==sha,rel
    base=ROOT/('inputs/panel' if args.panel else 'inputs/diagnostics')
    manifest=json.loads((base/'manifest.json').read_text())
    sessions=manifest['sessions']
    for session in sessions:
        directory=base/session['id'];rows=loadnp(directory/'rows.npz');events=loadnp(directory/'exact-events.npz')['events']
        # Removal intervention alone uses evaluator source interval. No labels enter children.
        labels=json.loads((directory/'evaluatorlabels.json').read_text())
        a,b=labels['source_interval'];remove=[int(u) for u in np.unique(rows['unit']) if u<b and u+1>a]
        modes=['full','recent','removed'] if args.panel and labels['positive'] else ['full']
        for method in ['D','G','G-exact']:
            for mode in modes:
                dest=ROOT/'outputs'/('panel' if args.panel else 'diagnostics')/session['id']/method/mode
                if (dest/'completed.json').exists():continue
                if dest.exists():raise RuntimeError('Interrupted exposed readout: preserve, do not replay '+str(dest))
                resource_guard();one_readout(rows,events,method,mode,remove,dest)
        print(session['id'],readout_count(),flush=True)
    write(ROOT/('panel-completed.json' if args.panel else 'diagnostics-completed.json'),resource_guard())
if __name__=='__main__':main()
