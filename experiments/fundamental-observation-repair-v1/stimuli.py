"""Evaluator only. Supplied note blocks; no metadata enters the worker."""
import numpy as np
import hashlib
CELLS=['matched','timbre','duration','joint']
CONDITIONS=['intact','reset','removal','swap','shuffle','ambiguous']
def wave(pitch,render):
    duration,amps,attack,decay,rms,phase=render
    n=round(16000*duration);t=np.arange(n)/16000;z=np.linspace(0,1,n)
    envelope=np.minimum(z/attack,1)*np.minimum((1-z)/decay,1)
    hz=220*2**(pitch/12)
    x=sum(a*np.sin(2*np.pi*hz*(j+1)*t+phase*(j+1)) for j,a in enumerate(amps))*envelope
    x*=rms/np.sqrt(np.mean(x*x))
    return x.astype('<f4').tobytes()
def group(entry):
    i=entry['tuple_id'];a,b,c,d=entry['motif'];base=float(entry['register'])
    Q=[base,base-a,base+b];R=[base,base-c,base+b];ends=[base+b-d,base+b+d]
    # Disjoint tuples for every group; heldout durations > all training durations.
    short=.10+i*.0007;long=.22+i*.0013
    phase=float(np.random.default_rng(entry['seed']).uniform(-2,2))
    simple=[1.] if entry['family']=='pure' else [1.,.08+i*.0002,.025]
    changed=[.25+i*.001,1.,.22+i*.001] if entry['rich'] else ([1.] if entry['family']=='pure' else [1.,.35,.18])
    render=lambda dur,amps,atk,dec:(dur,amps,atk,dec,entry['rms'],phase)
    cache={};episodes=[];params={}
    for cell in CELLS:
        demo=render(short,simple,.12,.22);cue=demo
        if cell in ('timbre','joint'):
            other=render(short,changed,.03+i*.0001,.55)
            demo,cue=(other,demo) if entry['direction'] else (demo,other)
        if cell in ('duration','joint'):cue=(long,*cue[1:])
        params[cell]={'demo':demo,'cue':cue}
        def sound(p,r):
            key=(p,str(r))
            if key not in cache:cache[key]=wave(p,r)
            return cache[key]
        silence=bytes(round(short*16000)*4)
        for condition in (CONDITIONS if cell=='joint' else ['intact']):
            for variant in [0,1]:
                binding=1-variant if condition=='swap' else variant
                qa=Q+[ends[binding]];rb=R+[ends[1-binding]]
                if condition=='ambiguous':qa=Q+[ends[0]];rb=Q+[ends[1]]
                chunks=[qa,rb] if entry['order']==0 else [rb,qa]
                if condition=='shuffle':chunks=chunks[::-1]
                pitches=chunks[0]+[None]+chunks[1]+[None,None]+Q
                blocks=[silence if p is None else sound(p,demo if j<11 else cue) for j,p in enumerate(pitches)]
                if condition=='removal':
                    for j in [3,8]:blocks[j]=silence;pitches[j]=None
                target=ends[variant] if condition=='ambiguous' else ends[binding]
                episodes.append(dict(family=cell,condition=condition,variant=variant,blocks=blocks,future=sound(target,cue),alternative_future=sound(ends[1-binding],cue),truth=dict(pitch_semitones=target,interval_semitones=target-Q[-1],outcome_intervals=[-d,d] if condition=='ambiguous' else [target-Q[-1]],outcome_probabilities=[.5,.5] if condition=='ambiguous' else [1.]),underlying_pitches=pitches,reset_before_index=11 if condition=='reset' else None,group_id=entry['group_id'],split=entry['split'],diagnostic_order=entry['order']))
    return episodes,dict(cue=Q,other_cue=R,continuations=ends,renderers=params,seed=entry['seed'],normalized_motif=entry['motif'],block_hashes={str(k):hashlib.sha256(v).hexdigest() for k,v in cache.items()})
