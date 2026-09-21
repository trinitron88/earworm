"""Waveform-only NSDF periodicity adapter; unchanged primary PR8 retrieval."""
import numpy as np
import reference_model as ref
CAPACITY=32
BASES=['present','recency','transition1','transition2','transition3','absolute','reference']
NAMES=[a+'_'+b for a in ['old','repaired'] for b in BASES]
def periodicity(raw,config):
    x=np.frombuffer(raw,dtype='<f4').astype(float);rms=float(np.sqrt(np.mean(x*x)));x=x-x.mean();n=len(x)
    size=1<<(2*n-1).bit_length();ft=np.fft.rfft(x,n=size);corr=np.fft.irfft(abs(ft)**2,n=size)[:n];cs=np.r_[0.,np.cumsum(x*x)]
    low=max(2,int(16000/config['max_hz']));high=min(n-2,int(16000/config['min_hz']))
    lags=np.arange(high+2);den=cs[n-lags]+cs[n]-cs[lags];nsdf=np.divide(2*corr[:high+2],den,out=np.zeros(high+2),where=den>1e-20)
    candidates=[]
    for k in range(low,high+1):
        if nsdf[k]>=nsdf[k-1] and nsdf[k]>nsdf[k+1]:
            div=nsdf[k-1]-2*nsdf[k]+nsdf[k+1];shift=.5*(nsdf[k-1]-nsdf[k+1])/div if div else 0.;lag=k+float(np.clip(shift,-.5,.5));hz=16000/lag
            candidates.append(dict(lag_samples=lag,hz=hz,periodicity=float(nsdf[k])))
    alternatives={}
    for threshold in config['threshold_grid']:
        accepted=[c for c in candidates if c['periodicity']>=threshold]
        c=accepted[0] if accepted and rms>=config['rms_floor'] else None
        alternatives[str(threshold)]={'pitch_hz':c['hz'] if c else None,'pitch_semitones':float(12*np.log2(c['hz']/220)) if c else None,'pitch_available':c is not None,'selected_periodicity':c['periodicity'] if c else None}
    chosen=alternatives[str(config['periodicity_threshold'])]
    return {**chosen,'candidate_fundamentals':candidates,'finite_grid_observations':alternatives,'rms':rms,'uncertainty':'Earliest local NSDF peak above fixed development threshold; later multiples remain reported, not separate independent pitches. No claim for missing fundamental/noisy/polyphonic signals. Unavailable if no sufficient peak or low RMS.'}
def observe(raw,config=None):
    if config is None:config={'periodicity_threshold':.9,'threshold_grid':[.85,.90,.95],'min_hz':80,'max_hz':2000,'rms_floor':.01}
    old=ref.observe(raw)
    return {**old,'repaired_observation':periodicity(raw,config)}
def model_spec(name,config):
    adapter,base=name.split('_',1);cfg=dict(config['reference']);cfg['calibration']=dict(cfg['calibration'])
    if base.startswith('transition'):source='transition';cfg['transition_order']=int(base[-1])
    elif base=='absolute':source='retrieval_absolute';cfg['retrieval_absolute_order']=3
    elif base=='reference':source='retrieval_transposed'
    else:source=base
    return adapter,source,cfg
def forecast(history,config):
    out={}
    for name in NAMES:
        adapter,source,cfg=model_spec(name,config)
        h=history if adapter=='old' else [{**o,**o['repaired_observation']} for o in history]
        f=ref.forecast(h,cfg)[source]
        f['lookup_evidence']=ref.candidates(h,source,cfg);f['adapter']=adapter
        out[name]=f
    return out
