"""Evaluator-only continuous PCM construction; chunks never expose these bounds."""
import numpy as np,hashlib
CELLS=['detached','legato','duration','joint']
CONDITIONS=['intact','reset','removal','swap','shuffle','ambiguous','unrelated']
RATE=16000;CHUNK=1024
def wave(pitch,n,amps,phase,detached=False):
    t=np.arange(n)/RATE;hz=220*2**(pitch/12);x=sum(a*np.sin(2*np.pi*hz*(j+1)*t+phase) for j,a in enumerate(amps));env=np.ones(n)
    # Detached gap belongs to its preceding note; legato has no zero region.
    if detached:env[-128:]=0.;env[:32]=np.linspace(0,1,32)
    else:env*=.88+.12*np.cos(np.pi*np.arange(n)/max(1,n-1))
    x*=env;x*=.10/np.sqrt(np.mean(x*x));return x.astype('<f4').tobytes()
def group(g):
    a,b,c,d=g['motif'];sgn=-1 if g['direction'] else 1;base=g['register'];Q=[base,base-a*sgn,base+(-a+b)*sgn];R=[base,base-c*sgn,Q[-1]];ends=[Q[-1]-d,Q[-1]+d];rng=np.random.default_rng(g['seed']);phase=float(rng.uniform(-2,2));episodes=[];recipes={}
    for cell in CELLS:
        # None of these durations are supplied to the operational process.
        n0=1401+g['index']*3
        durations=[n0,n0+113,n0+41,n0+79]
        if cell in ['duration','joint']:durations=[n0+37,n0+221,n0-107,n0+143]
        demoamps=[1.] if g['family']=='pure' else [1.,.08,.025];cueamps=demoamps
        if cell=='joint':
            other=[.28+g['index']*.001,1.,.25] if g['rich'] else ([1.] if g['family']=='pure' else [1.,.35,.18])
            demoamps,cueamps=(other,demoamps) if g['direction'] else (demoamps,other)
        cache={}
        def tone(p,j,current=False):
            ns=durations[j]+(83 if current and cell in ['duration','joint'] else 0);amps=cueamps if current else demoamps;key=(p,ns,tuple(amps))
            if key not in cache:cache[key]=wave(p,ns,amps,phase,cell=='detached')
            return cache[key]
        def event(p,j,current=False):return (tone(p,j,current),p)
        for cond in (CONDITIONS if cell=='joint' else ['intact']):
          for variant in [0,1]:
            binding=1-variant if cond=='swap' else variant;qa=Q+[ends[binding]];rb=R+[ends[1-binding]]
            if cond=='ambiguous':qa=Q+[ends[0]];rb=Q+[ends[1]]
            chunks=[[event(p,j) for j,p in enumerate(qa)],[event(p,j) for j,p in enumerate(rb)]]
            if cond=='removal':
                for chunk in chunks:chunk[3]=(bytes(len(chunk[3][0])),None)
            if g['order']:chunks=chunks[::-1]
            if cond=='shuffle':chunks=chunks[::-1]
            units=[(bytes(384*4),None)]+chunks[0]+[(bytes(896*4),None)]+chunks[1]
            preprobe=sum(len(x[0])//4 for x in units);units+=[(bytes(2048*4),None)]+[event(p,j,True) for j,p in enumerate(Q)]
            probeQ=Q if cond!='unrelated' else [base,base+2*sgn,base-7*sgn]
            if cond=='unrelated':units[-3:]=[event(p,j,True) for j,p in enumerate(probeQ)]
            probe_start=preprobe+2048;probe_end=sum(len(x[0])//4 for x in units);tail=2048;total=((probe_end+tail+CHUNK-1)//CHUNK)*CHUNK;units+=[(bytes((total-probe_end)*4),None)]
            raw=b''.join(x[0] for x in units);assert len(raw)//4<=32000 and len(raw)//(4*CHUNK)<=32
            bounds=[];start=0
            for z,pitch in units:bounds.append(dict(start=start,end=start+len(z)//4,pitch=pitch,wave_sha256=hashlib.sha256(z).hexdigest()));start+=len(z)//4
            reset=((preprobe+640+CHUNK-1)//CHUNK)*CHUNK if cond=='reset' else None
            assert reset is None or preprobe<reset<probe_start
            target=ends[variant] if cond=='ambiguous' else ends[binding]
            if cond=='unrelated':target=probeQ[-1]+([-d,d][binding])
            regions=[]
            for ix in [1,6]:
                if [z['pitch'] for z in bounds[ix:ix+3]]==Q and cond not in ['unrelated','reset']:
                    regions.append({'start':bounds[ix]['start'],'end':bounds[ix+2]['end'],'pitch_shift':0.,'time_ratio':(probe_end-probe_start)/(bounds[ix+2]['end']-bounds[ix]['start'])})
            episodes.append(dict(group=g['group_id'],cell=cell,condition=cond,variant=variant,prefix=raw,bounds=bounds,probe_start=probe_start,probe_end=probe_end,reset_sample=reset,future=tone(target,3,True),alternative_future=tone(ends[1-binding],3,True),truth=dict(pitch_semitones=target,prefix_true_pitches=probeQ,outcome_intervals=[-d,d] if cond=='ambiguous' else [target-probeQ[-1]],outcome_probabilities=[.5,.5] if cond=='ambiguous' else [1.],source_regions=regions,unrelated=cond=='unrelated',changed=cell in ['duration','joint'],expected_pitch_shift=0.)))
        recipes[cell]=dict(durations=durations,phase=phase,demo_harmonics=demoamps,cue_harmonics=cueamps,cache_hashes={str(k):hashlib.sha256(v).hexdigest() for k,v in cache.items()})
    return episodes,dict(group=g,normalized_Q=[x-Q[0] for x in Q],normalized_R=[x-R[0] for x in R],cells=recipes)
