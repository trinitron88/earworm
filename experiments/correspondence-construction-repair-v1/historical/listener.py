"""Arrived-audio-only child and saved-state matcher. No generator imports."""
import base64,io,json,sys,time,pickle,os,builtins,socket,resource
from collections import deque
import numpy as np
from matching import align,subsequence_dtw

def encode(state):
 b=io.BytesIO();np.savez_compressed(b,**state);return base64.b64encode(b.getvalue()).decode()
def decode(blob):
 with np.load(io.BytesIO(base64.b64decode(blob)),allow_pickle=False) as z:return {k:z[k] for k in z.files}
def smooth(x):
 y=np.empty_like(x,dtype=np.float64)
 for i in range(len(x)):
  # Trailing five-frame Hann statistics; contiguous segments handled separately.
  a=x[max(0,i-4):i+1];w=np.hanning(7)[1:6][-len(a):];y[i]=(a*w[:,None]).sum(0)/w.sum()
 return y/np.maximum(np.linalg.norm(y,axis=1,keepdims=True),1e-12)
def segments(times):
 if not len(times):return []
 cuts=np.r_[0,np.flatnonzero(np.diff(times)>.10001)+1,len(times)]
 return [(int(a),int(b)) for a,b in zip(cuts[:-1],cuts[1:])]
def predict(state,route):
 t=state['t'];rms=state['rms'];loud=np.flatnonzero(rms>1e-4)
 if not len(loud):return {'distance':None,'hypothesis':None,'reason':'no observed query'}
 end=t[loud[-1]];qi=np.flatnonzero((t>end-2.0+1e-8)&(t<=end+1e-8))
 if len(qi)<12:return {'distance':None,'hypothesis':None,'reason':'insufficient query'}
 hi=np.flatnonzero(state['unit']<state['unit'][qi[0]])
 key={'standard':'chroma','mert6':'mert6','mert12':'mert12','ceiling':'clean'}[route]
 feats=state[key];best=None
 for a,b in segments(t[hi]):
  ids=hi[a:b]
  if len(ids)<10:continue
  if route=='standard':
   # Recompute smoothing from remaining measurements, so removal leaves no cache.
   h=smooth(feats[ids]);q=smooth(feats[qi]);m=align(q,h,roll_chroma=True)
  elif route=='ceiling':
   q=feats[qi];h=feats[ids];candidates=[]
   for shift in range(-5,6):
    v=np.zeros_like(h)
    if shift>=0:v[:,shift:128]=h[:,:128-shift]
    else:v[:,:128+shift]=h[:,-shift:128]
    v[:,128]=h[:,128];m=subsequence_dtw(q,v);m['shift']=shift;candidates.append(m)
   m=min(candidates,key=lambda x:(x['cost'],abs(x['shift']),x['shift']))
  else:m=align(feats[qi],feats[ids]);m['shift']=None
  if not np.isfinite(m['cost']) or m['start_index'] is None or m['end_index'] is None:continue
  s=m['start_index'];e=m['end_index'];duration=(t[ids[e]]-t[ids[s]]+.1);ratio=(len(qi)*.1)/duration
  if not .65<=ratio<=1.5:continue
  shift=m['shift']
  if shift is None:
   # Hybrid MERT identity + common acoustic sidecar for transformation only.
   pairs=m['path'];costs=[]
   qc=smooth(state['chroma'][qi]);hc=smooth(state['chroma'][ids])
   for k in range(-5,6):costs.append((float(np.mean([1-np.dot(qc[i],np.roll(hc[j],k)) for i,j in pairs])),abs(k),k))
   shift=min(costs)[2]
  candidate={'distance':float(m['cost']),'hypothesis':{'start':float(t[ids[s]]-.05),'end':float(t[ids[e]]+.05),'shift':int(shift),'stretch':float(ratio),'path':[[int(qi[i]),int(ids[j])] for i,j in m['path']]},'query_support':[float(t[qi[0]]-.05),float(t[qi[-1]]+.05)],'query_context_support':[int(state['unit'][qi[0]]),int(state['unit'][qi[-1]])+1],'history_context_support':[int(state['unit'][ids[s]]),int(state['unit'][ids[e]])+1]}
  if best is None or candidate['distance']<best['distance']:best=candidate
 return best or {'distance':None,'hypothesis':None,'reason':'no admissible earlier sequence'}

def install_guard():
 def denied(*a,**k):raise PermissionError('listener file/network access disabled after initialization')
 builtins.open=denied;io.open=denied;os.open=denied;socket.socket=denied

def array_only():
 install_guard();print(json.dumps({'ready':True,'metadata':{'score_only':True}}),flush=True)
 for line in sys.stdin:
  cmd=json.loads(line);assert cmd['op']=='predict' and cmd['route']=='ceiling';state=decode(cmd['state']);start=time.monotonic();answer=predict(state,'ceiling');answer.update(compute_seconds=time.monotonic()-start,committed_monotonic=time.monotonic());print(json.dumps(answer),flush=True);del state,answer;cmd.clear();line=None

def main():
 if sys.argv[1]=='--score-only':return array_only()
 from features import spectral,MertFeatures
 engine=MertFeatures(sys.argv[1],sys.argv[2]);records=[];ring=deque(maxlen=4);clock=0;peak=0;install_guard()
 print(json.dumps({'ready':True,'metadata':engine.metadata}),flush=True)
 for line in sys.stdin:
  cmd=json.loads(line);op=cmd['op']
  if op=='reset':records.clear();ring.clear();clock=0;peak=0;print('{"reset":true}',flush=True);continue
  if op=='arrive':
   arrived=time.monotonic();pcm=np.frombuffer(base64.b64decode(cmd['pcm']),dtype='<f4').copy();assert pcm.shape==(24000,)
   ring.append(pcm);start=time.monotonic();sp=spectral(pcm);spectral_seconds=time.monotonic()-start;mf=engine.extract(pcm)
   record={'t':clock+np.arange(10)*.1+.05,'unit':np.full(10,clock,dtype=np.int32),'power':sp['power'],'rms':sp['rms'],'chroma':sp['chroma'],'mert6':mf['layer6'],'mert12':mf['layer12']}
   records.append(record);clock+=1
   # FIFO unit admission; entire record (including sidecar and all candidate states) counted.
   if len(records)>60:records.pop(0)
   statebytes=sys.getsizeof(records)+sum(sys.getsizeof(r)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in r.items()) for r in records)
   peak=max(peak,statebytes);assert statebytes<=8*1024**2
   encoded=encode(record);output={'arrived_monotonic':arrived,'serialized_monotonic':time.monotonic(),'spectral_seconds':spectral_seconds,'mert_seconds':engine.last_compute_seconds,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'audio_available_after_sample':clock*24000,'context_samples':[(clock-1)*24000,clock*24000],'retained_state_bytes':statebytes,'raw_ring_bytes':sum(x.nbytes for x in ring),'raw_ring_start_sample':max(0,clock-4)*24000,'ring_chunks':len(ring),'data':encoded}
   print(json.dumps(output),flush=True);del output,sp,mf,pcm,record,encoded;cmd.clear();line=None
  elif op=='finish':
   state={k:np.concatenate([r[k] for r in records]) for k in records[0]};print(json.dumps({'state':encode(state),'peak_state_bytes':peak,'raw_ring_start_sample':max(0,clock-4)*24000,'raw_ring_bytes':sum(x.nbytes for x in ring),'unit_replacements':max(0,clock-60)}),flush=True);records.clear();ring.clear();del state;cmd.clear();line=None
  elif op=='predict':
   assert cmd['route']!='ceiling';state=decode(cmd['state']);start=time.monotonic();answer=predict(state,cmd['route']);answer.update(compute_seconds=time.monotonic()-start,committed_monotonic=time.monotonic());print(json.dumps(answer),flush=True);del state,answer;cmd.clear();line=None
  else:raise ValueError(op)
if __name__=='__main__':main()
