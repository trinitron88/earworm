"""Evaluator-only synthesis; target PCM is generated after durable forecasts."""
import numpy as np,hashlib
CELLS=['unchanged','transpose','stretch','timbre'];CONDITIONS=['intact','reset','removal','swap','shuffle','ambiguous','unrelated'];RATE=16000;CHUNK=1024

def wave(pitch,n,amps,phase):
 t=np.arange(n)/RATE;hz=220*2**(pitch/12);x=sum(a*np.sin(2*np.pi*hz*(j+1)*t+phase) for j,a in enumerate(amps));env=.88+.12*np.cos(np.pi*np.arange(n)/max(1,n-1));x*=env;x*=.1/np.sqrt(np.mean(x*x));return x.astype('<f4').tobytes()
def render(spec):return wave(**spec)
def group(g):
 a,b,c,d=g['motif'];sign=-1 if g['direction'] else 1;base=g['register'];Q=[base,base-a*sign,base+(-a+b)*sign];R=[base,base-c*sign,Q[-1]];ends=[Q[-1]-d,Q[-1]+d];phase=float(np.random.default_rng(g['seed']).uniform(-2,2));episodes=[];recipes={}
 for cell in CELLS:
  n0=1357+g['index']*3;durations=[n0,n0+113,n0+41,n0+79];shift=g['transpose'] if cell=='transpose' else 0;ratio=g['stretch'] if cell=='stretch' else 1.
  amps=[1.] if g['family']=='pure' else ([1.,.12,.04] if g['family']=='fundamental' else [.6,1.,.25]);cue=([1.,.5,.3] if g['family']=='pure' else [1.,.04,.01]) if cell=='timbre' else amps
  cache={}
  def spec(p,j,current=False):return dict(pitch=p,n=round(durations[j]*(ratio if current else 1)),amps=cue if current else amps,phase=phase)
  def event(p,j,current=False):
   s=spec(p,j,current);key=str(s)
   if key not in cache:cache[key]=render(s)
   return (cache[key],p)
  for cond in (CONDITIONS if cell=='unchanged' else ['intact']):
   for variant in [0,1]:
    binding=1-variant if cond=='swap' else variant;qa=Q+[ends[binding]];rb=R+[ends[1-binding]]
    if cond=='ambiguous':qa=Q+[ends[0]];rb=Q+[ends[1]]
    chunks=[[event(p,j) for j,p in enumerate(qa)],[event(p,j) for j,p in enumerate(rb)]]
    if cond=='removal':
     for chunk in chunks:chunk[3]=(bytes(len(chunk[3][0])),None)
    if g['order']:chunks=chunks[::-1]
    if cond=='shuffle':chunks=chunks[::-1]
    units=[(bytes(384*4),None)]+chunks[0]+[(bytes(896*4),None)]+chunks[1];preprobe=sum(len(x[0])//4 for x in units)
    probeQ=[p+shift for p in Q] if cond!='unrelated' else [base,base+2*sign,base-7*sign]
    units+=[(bytes(2048*4),None)]+[event(p,j,True) for j,p in enumerate(probeQ)];probe_start=preprobe+2048;probe_end=sum(len(x[0])//4 for x in units);total=((probe_end+2048+CHUNK-1)//CHUNK)*CHUNK;units+=[(bytes((total-probe_end)*4),None)]
    raw=b''.join(x[0] for x in units);assert len(raw)//4<=32000
    bounds=[];start=0
    for z,p in units:bounds.append(dict(start=start,end=start+len(z)//4,pitch=p,wave_sha256=hashlib.sha256(z).hexdigest()));start+=len(z)//4
    reset=((preprobe+640+CHUNK-1)//CHUNK)*CHUNK if cond=='reset' else None;target=(ends[variant] if cond=='ambiguous' else ends[binding])+shift
    if cond=='unrelated':target=probeQ[-1]+[-d,d][binding]
    regions=[]
    for ix in [1,6]:
     if [z['pitch'] for z in bounds[ix:ix+3]]==Q and cond not in ['unrelated','reset']:regions.append({'start':bounds[ix]['start'],'end':bounds[ix+2]['end'],'pitch_shift':shift,'time_ratio':(probe_end-probe_start)/(bounds[ix+2]['end']-bounds[ix]['start'])})
    episodes.append(dict(group=g['group_id'],cell=cell,condition=cond,variant=variant,prefix=raw,bounds=bounds,probe_start=probe_start,probe_end=probe_end,reset_sample=reset,future_spec=spec(target,3,True),alternative_spec=spec(ends[1-binding]+shift,3,True),truth=dict(pitch_semitones=target,prefix_true_pitches=probeQ,outcome_intervals=[-d,d] if cond=='ambiguous' else [target-probeQ[-1]],outcome_probabilities=[.5,.5] if cond=='ambiguous' else [1.],source_regions=regions,unrelated=cond=='unrelated',changed=cell!='unchanged',expected_pitch_shift=shift,expected_time_ratio=ratio,expected_timbre_changed=cell=='timbre')))
  recipes[cell]=dict(durations=durations,phase=phase,demo_harmonics=amps,cue_harmonics=cue,shift=shift,ratio=ratio,source_cache_hashes={str(k):hashlib.sha256(v).hexdigest() for k,v in cache.items()})
 return episodes,dict(group=g,cells=recipes)
