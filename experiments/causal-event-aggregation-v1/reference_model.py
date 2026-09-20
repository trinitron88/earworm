"""Isolated acoustic observations and six causal predictors. No generator imports."""
import hashlib
import math
import numpy as np

NAMES = ['present', 'recency', 'transition', 'retrieval_absolute', 'retrieval_transposed', 'relational']
BINS = np.arange(-24, 25, dtype=float)
CAPACITY = 32


def observe(raw, rate=16000):
    x = np.frombuffer(raw, dtype='<f4').astype(float)
    rms = float(np.sqrt(np.mean(x*x)))
    spectrum = abs(np.fft.rfft(x*np.hanning(len(x)), n=16384))
    freq = np.fft.rfftfreq(16384, 1/rate)
    allowed = np.flatnonzero((freq >= 80) & (freq <= 4000))
    k = int(allowed[np.argmax(spectrum[allowed])])
    y = np.log(np.maximum(spectrum[k-1:k+2], 1e-30))
    shift = float(.5*(y[0]-y[2])/(y[0]-2*y[1]+y[2])) if y[0]-2*y[1]+y[2] else 0.
    hz = (k+shift)*rate/16384
    concentration = float(spectrum[max(0,k-12):k+13].sum()/max(spectrum.sum(),1e-30))
    valid = rms >= .01 and concentration >= .3
    return dict(wave_sha256=hashlib.sha256(raw).hexdigest(), sample_count=len(x), duration_s=len(x)/rate,
                rms=rms, spectral_peak_hz=float(hz), pitch_hz=float(hz) if valid else None,
                pitch_semitones=12*math.log2(hz/220) if valid else None,
                spectral_concentration=concentration, pitch_available=bool(valid),
                uncertainty='single clean-block spectral estimate; unavailable below fixed RMS/concentration gates; not a verified note')


def candidates(history, name, config):
    """Only observed keys AND their already-observed successors can enter memory."""
    if not history or history[-1]['pitch_semitones'] is None:
        return []
    if name == 'present':
        return []
    length = 1 if name == 'recency' else config.get(name+'_order', 3)
    if len(history) < length+1:
        return []
    key = [h['pitch_semitones'] for h in history[-length:]]
    if any(p is None for p in key):
        return []
    q = np.array(key)
    possible = []
    for start in range(len(history)-length):
        seq = [h['pitch_semitones'] for h in history[start:start+length+1]]
        if any(p is None for p in seq):
            continue
        past, following = np.array(seq[:-1]), seq[-1]
        if name in ('present','recency','transition','retrieval_absolute'):
            distance = float(np.max(abs(past-q)))
            interval = following-q[-1]
        elif name == 'retrieval_transposed':
            shift = float(np.mean(q-past))
            distance = float(np.max(abs(past+shift-q)))
            interval = following+shift-q[-1]
        else:
            # Pairwise interval geometry, rather than absolute positions.
            ix = [(i,j) for i in range(length) for j in range(i+1,length)]
            distance = float(np.sqrt(np.mean([(past[j]-past[i]-(q[j]-q[i]))**2 for i,j in ix])))
            interval = following-past[-1]
        if distance <= config.get(name+'_cutoff', .3):
            possible.append({'distance':distance,'interval':float(interval),'source_start':start})
    if name == 'recency' and possible:
        possible = [possible[-1]]
    return possible


def distribution(atoms, name, config, anchor):
    prior = np.asarray(config['prior'],dtype=float)
    if anchor is None:
        p = np.zeros(50);p[-1]=1.;return p
    cal = config.get('calibration',{}).get(name, {'temperature':.1,'sigma':.2,'floor':.01})
    if not atoms:
        p = prior.copy()
    else:
        weights = np.exp(-np.asarray([a['distance'] for a in atoms])/cal['temperature']);weights/=weights.sum()
        p=np.zeros(50)
        for w,a in zip(weights,atoms):
            if a['interval'] < -24.5 or a['interval'] > 24.5:
                p[-1]+=w
            else:
                masses=np.exp(-.5*((BINS-a['interval'])/cal['sigma'])**2)
                if masses.sum() == 0:
                    p[-1]+=w
                else:
                    p[:-1]+=w*masses/masses.sum()
    p=(1-cal['floor'])*p+cal['floor']/50
    return p/p.sum()


def forecast(history, config):
    anchor=history[-1]['pitch_semitones'] if history else None
    outputs={}
    for name in NAMES:
        atoms=candidates(history,name,config)
        p=distribution(atoms,name,config,anchor)
        mode=int(np.argmax(p)); interval=None if mode==49 else int(BINS[mode])
        outputs[name]={'probabilities':p.tolist(),'point_interval_semitones':interval,
                       'point_pitch_semitones':None if interval is None or anchor is None else anchor+interval,
                       'anchor_semitones':anchor,'matched_memory_entries':len(atoms),
                       'search_entries_examined':max(0,len(history)-(1 if name=='recency' else config.get(name+'_order',3))) if name!='present' else 0}
    return outputs
