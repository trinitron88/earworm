"""Evaluator-only deterministic fresh stimuli; never imported by the predictor."""
import hashlib
import numpy as np

CONDITIONS=['intact','reset','removal','swap','shuffle','ambiguous']

def wave(pitch, amp, harmonic, phase):
    t=np.arange(1920)/16000
    hz=220*2**(pitch/12)
    envelope=np.sin(np.pi*np.arange(1920)/1919)**2
    return (amp*envelope*(np.sin(2*np.pi*hz*t+phase)+harmonic*np.sin(4*np.pi*hz*t+.3))).astype('<f4').tobytes()

def group(entry):
    rng=np.random.default_rng(entry['seed'])
    base=float(rng.uniform(-9,-6)); u=float(rng.choice([2,3,4,5])); w=float(rng.choice([x for x in [2,3,4,5] if x!=u])); v=float(rng.choice([8,9,10,11]));delta=float(rng.choice([d for d in [4,5] if v-d != u]))
    amp=float(rng.uniform(.20,.28));harmonic=float(rng.uniform(.08,.15));phase=float(rng.uniform(-np.pi,np.pi))
    cache={}
    def sound(p):
        if p not in cache:cache[p]=wave(p,amp,harmonic,phase)
        return cache[p]
    Q=[base,base+u,base+v];R=[base,base+w,base+v];ends=[base+v-delta,base+v+delta]
    pads=[base-2,base-1,base+1,base+6]
    gap=int(rng.integers(0,5)); lead=int(rng.integers(0,5-gap));trail=4-gap-lead
    order=entry['order']; shift=entry['transfer_shift']
    episodes=[]
    for family,sh in [('basic',0),('transfer',shift)]:
        cue=[p+sh for p in Q]
        for condition in CONDITIONS:
            for variant in [0,1]:
                binding=1-variant if condition=='swap' else variant
                a=Q+[ends[binding]];b=R+[ends[1-binding]]
                if condition=='ambiguous':a=Q+[ends[0]];b=Q+[ends[1]]
                chunks=[a,b] if order==0 else [b,a]
                if condition=='shuffle':chunks=chunks[::-1]
                pitches=pads[:lead]+chunks[0]+pads[lead:lead+gap]+chunks[1]+pads[lead+gap:]+cue
                assert len(pitches)==15
                if condition=='ambiguous':target=ends[variant]+sh
                else:target=ends[binding]+sh
                blocks=[sound(p) for p in pitches]
                if condition=='removal':
                    for ix in [lead+3,lead+4+gap+3]:blocks[ix]=bytes(1920*4)
                truth={'pitch_semitones':target,'interval_semitones':target-cue[-1],
                       'outcome_intervals':[-delta,delta] if condition=='ambiguous' else [target-cue[-1]],
                       'outcome_probabilities':[.5,.5] if condition=='ambiguous' else [1.]}
                episodes.append({'family':family,'condition':condition,'variant':variant,'blocks':blocks,'future':sound(target),
                    'alternative_future':sound(ends[1-binding]+sh), 'truth':truth,
                    'underlying_pitches':pitches,'reset_before_index':12 if condition=='reset' else None,
                    'group_id':entry['group_id'],'split':entry['split'],'diagnostic_order':order})
    return episodes, {'base':base,'cue':Q,'other_cue':R,'continuations':ends,'padding':pads,'padding_layout':[lead,gap,trail],
                      'amplitude':amp,'harmonic':harmonic,'phase':phase,'transfer_shift':shift,
                      'block_hashes':{str(p):hashlib.sha256(raw).hexdigest() for p,raw in cache.items()}}
