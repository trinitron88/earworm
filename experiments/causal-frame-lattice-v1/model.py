"""Fixed-cadence lattice readout; event fronts are separate frozen comparators."""
import numpy as np,time,hashlib,math,json
import aggregation_front as old
accepted=old.accepted
observation=old.observation
predict=old.predict
NAMES=old.NAMES+['single']

def shape(raw):
    x=np.frombuffer(raw,dtype='<f4');power=abs(np.fft.rfft(x*np.hanning(len(x))))**2
    bins=np.array_split(power,8);v=np.array([float(z.sum()) for z in bins]);return (v/max(float(v.sum()),1e-20)).tolist()

def lattice_predict(frames,cfg,absolute=False,single=False):
    live=[i for i,f in enumerate(frames) if f['observation']['rms']>=.01]
    if not live:return empty(),[]
    end=live[-1];n=1 if single else cfg['query_frames'];start=end-n+1
    if start<0:return empty(),[]
    q=frames[start:end+1];qp=np.array([f['observation']['pitch_semitones'] if f['observation']['pitch_semitones'] is not None else np.nan for f in q]);anchor=next((f['observation']['pitch_semitones'] for f in reversed(q) if f['observation']['pitch_semitones'] is not None),None)
    if anchor is None:return empty(),[]
    candidates=[]
    for length in ([1] if single else cfg['alignment_lengths']):
      for lo in range(max(0,start-length-max(cfg['forecast_lag_frames'])+1)):
        hi=lo+length-1
        ix=np.rint(np.linspace(lo,hi,n)).astype(int);prior=[frames[int(i)] for i in ix];pp=np.array([f['observation']['pitch_semitones'] if f['observation']['pitch_semitones'] is not None else np.nan for f in prior]);valid=np.isfinite(qp)&np.isfinite(pp);coverage=float(valid.mean())
        if coverage<cfg['alignment_min_coverage']:continue
        shift=0. if absolute else float(np.median(qp[valid]-pp[valid]));residual=float(np.mean(abs(qp[valid]-pp[valid]-shift)));spectral=float(np.mean([sum(abs(a-b) for a,b in zip(x['spectral_shape'],y['spectral_shape']))/2 for x,y in zip(q,prior)]));energy=float(np.mean([abs(math.log(max(x['observation']['rms'],1e-8)/max(y['observation']['rms'],1e-8))) for x,y in zip(q,prior)]));cost=residual+2*(1-coverage)+.05*spectral+.02*energy
        if cost>cfg['alignment_max_cost']:continue
        future=[frames[hi+j]['observation']['pitch_semitones'] for j in cfg['forecast_lag_frames']];future=[v for v in future if v is not None]
        if not future:continue
        candidates.append({'cost':cost,'source_first_frame':lo,'source_last_frame':hi,'query_first_frame':start,'query_last_frame':end,'source_start_sample':frames[lo]['start_sample'],'source_end_sample':frames[hi]['end_sample'],'query_start_sample':q[0]['start_sample'],'query_end_sample':q[-1]['end_sample'],'pitch_shift':shift,'time_ratio':n/length,'spectral_difference':spectral,'energy_log_ratio_abs':energy,'coverage':coverage,'pitch_residual':residual,'prediction_pitch':float(np.median(future))+shift,'aligned_frame_indices':ix.tolist()})
    candidates.sort(key=lambda z:(z['cost'],z['source_first_frame'],z['source_last_frame']));chosen=[]
    for c in candidates:
        if all(c['source_last_frame']<v['source_first_frame'] or c['source_first_frame']>v['source_last_frame'] for v in chosen):chosen.append(c)
        if len(chosen)>=cfg['max_matches']:break
    probs=[0.]*50
    if not chosen:probs[-1]=1.
    else:
        weights=[math.exp(-c['cost']/cfg['alignment_temperature']) for c in chosen];total=sum(weights)
        for c,w in zip(chosen,weights):
            delta=c['prediction_pitch']-anchor;v=[math.exp(-.5*((k-delta)/.08)**2) for k in range(-24,25)];s=sum(v)
            if s<=0:probs[-1]+=w/total
            else:
                for j,m in enumerate(v):probs[j]+=w/total*m/s
        probs=[.999*v+.001/50 for v in probs]
    mode=max(range(50),key=probs.__getitem__);return {'anchor_semitones':anchor,'probabilities':probs,'point_pitch_semitones':None if mode==49 else anchor+mode-24,'lookup_evidence':chosen,'search_candidate_count':len(candidates),'search_serialized_candidate_bytes':sum(len(json.dumps(c,separators=(',',':'))) for c in candidates)},chosen

def empty():return {'anchor_semitones':None,'probabilities':[0.]*49+[1.],'point_pitch_semitones':None,'lookup_evidence':[]}

class Listener(old.Listener):
    def __init__(self,cfg):
        super().__init__(cfg);self.lattice={q['id']:[] for q in cfg['lattice_grid'] if cfg['lattice_development'] or q['id']==cfg['selected_lattice']};self.lattice_next={q['id']:q['samples'] for q in cfg['lattice_grid'] if q['id'] in self.lattice};self.lattice_calls=0
    def reset(self):
        super().reset();self.lattice={q['id']:[] for q in self.cfg['lattice_grid'] if self.cfg['lattice_development'] or q['id']==self.cfg['selected_lattice']};self.lattice_next={q['id']:self.total+q['samples'] for q in self.cfg['lattice_grid'] if q['id'] in self.lattice}
    def arrive(self,raw):
        response=super().arrive(raw)
        for q in self.cfg['lattice_grid']:
            key=q['id']
            if key not in self.lattice:continue
            while self.lattice_next[key]<=self.total:
                end=self.lattice_next[key];lo=end-q['samples'];block=self.raw[(lo-self.offset)*4:(end-self.offset)*4];obs=observation(block,self.cfg);self.lattice_calls+=1;shp=shape(block);mass=max(0.,min(1.,obs['selected_periodicity'])) if obs['pitch_semitones'] is not None else 0.
                self.lattice[key].append({'start_sample':lo,'end_sample':end,'available_sample':self.total,'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'observation':obs,'spectral_shape':shp,'pitch_distribution':{'candidate':obs['pitch_semitones'],'probability':mass,'unknown_mass':1-mass}});self.lattice_next[key]+=q['hop'];assert len(self.lattice[key])<=self.cfg['lattice_capacity']
        return response
    def forecast(self):
        result=super().forecast();result['lattice']=self.lattice
        for key,frames in self.lattice.items():
            base=predict([{'observation':f['observation']} for f in frames],self.cfg)
            base['absolute'],_=lattice_predict(frames,self.cfg,absolute=True)
            base['reference'],_=lattice_predict(frames,self.cfg)
            base['single'],_=lattice_predict(frames,self.cfg,single=True)
            result['forecasts'][key]=base
        result['lattice_observation_calls']=self.lattice_calls;return result
