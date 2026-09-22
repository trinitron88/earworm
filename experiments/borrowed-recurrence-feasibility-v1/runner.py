"""Evaluator broker. It owns truth/archives; the guarded listener receives PCM only."""
import argparse,base64,hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path
import numpy as np
from listener import encode,decode
from materials import split_manifest,make_session
ROOT=Path(__file__).resolve().parent
PYTHON=sys.executable
MODEL=Path(os.environ.get('EARWORM_LOCAL_MERT','/Users/bsantisi/Documents/Codex/2026-09-13/i/work/models/mert'))

def dump(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def commit_line(f,obj):
 f.write(json.dumps(obj,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())

def independent_sidecar(pcm,state):
 # Independent evaluator reconstruction: loops over frames/bins instead of feature helper.
 freq=np.arange(2049)*24000/4096;notes=np.full(2049,-1,dtype=int)
 notes[1:]=np.floor(69+12*np.log2(freq[1:]/440)+.5).astype(int)
 hann=np.hanning(2400);den=4096*sum(hann*hann);out=[];energies=[]
 for i in range(len(state['t'])):
  index=int(round((state['t'][i]-.05)*24000));x=pcm[index:index+2400].astype(float)
  z=np.fft.rfft(x*hann,n=4096);a=np.abs(z)**2/den;a[1:-1]*=2
  out.append([float(sum(a[notes==n])) for n in range(24,105)])
  energies.append(float(np.sqrt(sum(x*x)/len(x))))
 power=np.array(out);rms=np.array(energies)
 er=float(np.max(np.abs(power-state['power'])/np.maximum(np.abs(power),1e-20)))
 rr=float(np.max(np.abs(rms-state['rms'])/np.maximum(np.abs(rms),1e-20)))
 time_ok=bool(np.allclose(state['t'],state['unit']+.05+np.tile(np.arange(10)*.1,len(state['unit'])//10),rtol=0,atol=1e-10))
 return {'power_max_relative_error':er,'rms_max_relative_error':rr,'timestamp_support_pass':time_ok,'pass':er<=1e-6 and rr<=1e-6 and time_ok}

def subset(state,condition,labels,total):
 if condition=='full':keep=np.ones(len(state['t']),bool)
 elif condition=='recent':keep=state['unit']>=total-4
 elif condition=='removed':keep=~((state['unit']<labels['source_offset'])&(state['unit']+1>labels['source_onset']))
 else:raise ValueError(condition)
 return {k:v[keep] for k,v in state.items()}

class Child:
 def __init__(self,out,score_only=False):
  self.err=(out/('ceiling-stderr.txt' if score_only else 'listener-stderr.txt')).open('a')
  env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
  args=[PYTHON,str(ROOT/'listener.py')]+(['--score-only'] if score_only else [str(MODEL),str(out/'runtime-cache')])
  self.p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.err,text=True,env=env,bufsize=1)
  self.ready=self.read()
 def read(self):
  line=self.p.stdout.readline()
  if not line:raise RuntimeError('listener ended; inspect stderr; no automatic restart')
  obj=json.loads(line);obj['broker_received_monotonic']=time.monotonic();return obj
 def ask(self,obj):
  self.p.stdin.write(json.dumps(obj,separators=(',',':'))+'\n');self.p.stdin.flush();return self.read()
 def close(self):
  self.p.stdin.close();self.p.wait(timeout=30);self.err.close()

def run(split,limit=None):
 out=ROOT/'results'/split;out.mkdir(parents=True,exist_ok=True)
 if split=='evaluation':
  freeze=json.loads((ROOT/'freeze.json').read_text());receipt=json.loads((ROOT/'preregistration_receipt.json').read_text())
  assert receipt['posted'] and freeze['evaluation_exposed'] is False
  for name,h in freeze['hashes'].items():assert sha(ROOT/name)==h,(name,'changed after freeze')
  selection=json.loads((ROOT/'selection.json').read_text())
 else:selection=None
 manifest=split_manifest();dump(ROOT/'split.json',manifest) if split=='development' else None
 groups=[g for g in manifest['groups'] if g['split']==split]
 started=time.monotonic();child=Child(out);scorechild=Child(out,True);dump(out/'runtime.json',child.ready)
 records=[];summaries=[];calls=0
 donefile=out/'completed.json';done=json.loads(donefile.read_text()) if donefile.exists() else []
 try:
  for group in groups:
   for cell in manifest['cells']:
    key=group['id']+'-'+cell;d=out/key
    if key in done:
     records.extend(json.loads((d/'records.json').read_text()));summaries.append(json.loads((d/'summary.json').read_text()));continue
    if limit is not None and len(done)>=limit:break
    d.mkdir(exist_ok=True);t0=time.monotonic();pcm,ceiling,labels=make_session(group,cell,allow_evaluation=split=='evaluation')
    assert pcm.dtype==np.float32 and len(pcm)%24000==0
    total=len(pcm)//24000;np.savez_compressed(d/'audio.npz',pcm=pcm)
    # Truth is evaluator-owned and not written beside committed predictions until they exist.
    child.ask({'op':'reset'});availability=0.;unitlogs=[];sp=0.;mert=0.
    for u in range(total):
     sent=time.monotonic();r=child.ask({'op':'arrive','pcm':base64.b64encode(pcm[u*24000:(u+1)*24000].tobytes()).decode()});receive=r['broker_received_monotonic']
     r.pop('data');elapsed=receive-sent;availability=max(u+1,availability)+elapsed
     r.update(broker_sent_monotonic=sent,roundtrip_seconds=elapsed,real_time_simulated_available_seconds=availability,unit=u)
     unitlogs.append(r);sp+=r['spectral_seconds'];mert+=r['mert_seconds']
    finished=child.ask({'op':'finish'});state=decode(finished.pop('state'))
    # finish erases live records and raw ring; readout gets only each sanitized state.
    np.savez_compressed(d/'measurements.npz',**state);np.savez_compressed(d/'ceiling.npz',**ceiling)
    preservation=independent_sidecar(pcm,state)
    dump(d/'arrival-log.json',unitlogs)
    srecords=[];qend=float(labels['query_offset']);lastcontext=next(r for r in unitlogs if r['audio_available_after_sample']>=int(np.ceil(qend*24000)))
    route_list=['standard','mert6','mert12','ceiling'] if split=='development' else ['standard',selection['selected_mert'],'ceiling']
    # During development both MERT candidates are measured once in all controls; this spends the explicit 96-candidate reserve.
    with (d/'response-before-labels.jsonl').open('w') as f:
     for route in route_list:
      source=ceiling if route=='ceiling' else state
      for condition in ('full','recent','removed'):
       sub=subset(source,condition,labels,total);sent=time.monotonic();response=(scorechild if route=='ceiling' else child).ask({'op':'predict','route':route,'state':encode(sub)});calls+=1
       elapsed=time.monotonic()-sent
       response['readout_roundtrip_seconds']=elapsed
       # Independent readouts start at common audio decision time; unrelated ablation work does not inflate route latency.
       response['decision_latency_seconds']=max(0.,availability-qend)+elapsed
       response['end_to_end_compute_seconds']=(0. if route=='ceiling' else sp+(mert if route.startswith('mert') else 0.))+elapsed
       response['rtf']=response['end_to_end_compute_seconds']/(len(pcm)/24000)
       payload={'group':group['id'],'stratum':group['stratum'],'cell':cell,'route':route,'condition':condition,'prediction':response}
       commit_line(f,{'type':'response','value':payload,'committed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
       commit_line(f,{'type':'labels','value':labels});payload['labels']=labels;srecords.append(payload)
    dump(d/'records.json',srecords);dump(d/'labels.json',labels)
    source_units=np.unique(state['unit'][(state['t']>=labels['source_onset'])&(state['t']<labels['source_offset'])]).tolist()
    coverage=float(np.mean((state['t']>=labels['source_onset'])&(state['t']<labels['source_offset'])))
    summary={'group':group['id'],'cell':cell,'seconds':len(pcm)/24000,'session_wall_seconds':time.monotonic()-t0,'executions':len(srecords),'spectral_seconds':sp,'mert_seconds':mert,'preservation':preservation,'source_units_retained':source_units,'source_frame_count':int(coverage*len(state['t'])+.5),'source_pcm_evicted':finished['raw_ring_start_sample']>labels['source_offset']*24000,'finish':finished,'peak_rss_bytes':max(r['peak_rss_bytes'] for r in unitlogs),'peak_raw_ring_chunks':max(r['ring_chunks'] for r in unitlogs),'extraction_roundtrip_seconds':sum(r['roundtrip_seconds'] for r in unitlogs),'last_required_query_context':lastcontext['context_samples'],'input_sha256':sha(d/'audio.npz'),'measurements_sha256':sha(d/'measurements.npz')}
    dump(d/'summary.json',summary);summaries.append(summary);records.extend(srecords);done.append(key);dump(donefile,done)
    dump(out/'records.json',records);dump(out/'summaries.json',summaries)
    print(json.dumps({'completed':key,'sessions':len(done),'executions':len(records),'wall_seconds':round(time.monotonic()-started,2)}),flush=True)
   if limit is not None and len(done)>=limit:break
 finally:child.close();scorechild.close()
 dump(out/'run.json',{'split':split,'new_wall_seconds':time.monotonic()-started,'new_executions':calls,'completed_sessions':len(done),'broker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('split',choices=['development','evaluation']);p.add_argument('--limit',type=int);a=p.parse_args();run(a.split,a.limit)
