"""Common absolute semitone bins, unknown prediction, explicit out-of-range truth."""
import math
LOW=-48;HIGH=72;UNKNOWN=121

def absolute_distribution(f):
    p=[0.]*122;anchor=f['anchor_semitones']
    if anchor is None:p[UNKNOWN]=1.;return p
    for j,mass in enumerate(f['probabilities']):
        k=None if j==49 else round(anchor+j-24)
        ix=UNKNOWN if k is None or not LOW<=k<=HIGH else k-LOW
        p[ix]+=mass
    return p

def target_distribution(t):
    y=[0.]*122;outside=0.
    for delta,mass in zip(t['outcome_intervals'],t['outcome_probabilities']):
        absolute=t['prefix_true_pitches'][-1]+delta;k=round(absolute)
        if not LOW<=k<=HIGH:outside+=mass
        else:y[k-LOW]+=mass
    return y,outside

def measure(f,t):
    p=absolute_distribution(f);y,outside=target_distribution(t)
    assert all(math.isfinite(x) and x>=0 for x in p) and abs(sum(p)-1)<1e-10
    ll=math.inf if outside>0 else 0.
    for prob,mass in zip(p,y):
        if mass>0:ll+=-mass*math.log(prob) if prob>0 else math.inf
    # Outside truth is a separate known but unsupported category (zero forecast mass).
    brier=sum((a-b)**2 for a,b in zip(p,y))+outside**2+1-sum(x*x for x in y)-outside**2
    point=f['point_pitch_semitones']
    return dict(accuracy=float(point is not None and abs(point-t['pitch_semitones'])<=.35),log_loss=ll,brier=brier)

def safe(x):
    if isinstance(x,float) and not math.isfinite(x):
        if x==math.inf:return '+Infinity'
        if x==-math.inf:return '-Infinity'
        raise ValueError('NaN is not a scientific score')
    if isinstance(x,dict):return {k:safe(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [safe(v) for v in x]
    return x

def selftest():
    p=[0.]*50;p[24]=1.;f=dict(anchor_semitones=0.,probabilities=p,point_pitch_semitones=0.)
    def truth(v):return dict(prefix_true_pitches=[0.],outcome_intervals=[v],outcome_probabilities=[1.],pitch_semitones=v)
    assert measure(f,truth(1))['log_loss']==math.inf
    unavailable={**f,'anchor_semitones':None,'point_pitch_semitones':None}
    assert measure(unavailable,truth(0))['log_loss']==math.inf and measure(unavailable,truth(0))['accuracy']==0
    assert measure(f,truth(100))['log_loss']==math.inf
    p=[0.]*50;p[23]=p[25]=.5;amb={**f,'probabilities':p};t={**truth(-1),'outcome_intervals':[-1,1],'outcome_probabilities':[.5,.5]}
    assert abs(measure(amb,t)['log_loss']-math.log(2))<1e-12 and abs(measure(amb,t)['brier']-.5)<1e-12
    assert measure({**f,'anchor_semitones':12.,'point_pitch_semitones':12.},truth(0))['log_loss']==math.inf
    import json
    assert json.loads(json.dumps(safe({'loss':math.inf}),allow_nan=False))['loss']=='+Infinity'
    return dict(zero_probability=True,unavailable_anchor=True,out_of_range=True,ambiguity=True,octave_mapping=True,positive_infinity_serialization=True)
if __name__=='__main__':
    import json;print(json.dumps(selftest()))
