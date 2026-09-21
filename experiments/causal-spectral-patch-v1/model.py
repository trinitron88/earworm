"""Arrived-only spectral-patch identity and separate realization; no event inference."""
import numpy as np,time,hashlib,json,math
import frozen_lattice as old
accepted=old.accepted;observation=old.observation;predict=old.predict

def feature(raw,matrix,cfg):
 x=np.frombuffer(raw,dtype='<f4').astype(float);power=abs(np.fft.rfft(x*np.hanning(len(x)),n=cfg['patch_fft']))**2
 bands=matrix@power;total=float(bands.sum());energy=float(np.sqrt(np.mean(x*x)));log=np.log1p(cfg['patch_log_gain']*bands/max(total,cfg['patch_floor']));norm=float(np.sqrt(np.sum(log*log)));identity=log/max(norm,cfg['patch_floor'])
 return {'band_power':bands.tolist(),'identity':identity.tolist(),'rms':energy,'power_sum':total,'status':'captured_silence' if energy<cfg['patch_silence_rms'] else 'captured_sound'}

def empty(anchor=None):return {'anchor_semitones':anchor,'probabilities':[0.]*49+[1.],'point_pitch_semitones':None,'lookup_evidence':[],'search_candidate_count':0,'search_scratch_array_bytes':0}

def search(frames,cfg,absolute=False):
 live=[i for i,f in enumerate(frames) if f['channels']['s64']['rms']>=cfg['patch_silence_rms']]
 if not live:return empty()
 end=live[-1];n=cfg['patch_query_frames'];start=end-n+1
 if start<0:return empty()
 q=frames[start:end+1];anchor=next((f['pitch_readout'] for f in reversed(q) if f['pitch_readout'] is not None),None)
 if anchor is None:return empty()
 channels=cfg['_active_channels'];X=np.array([[f['channels'][k]['identity'] for k in channels] for f in frames]);Q=X[start:end+1];B=X.shape[-1];candidates=[];scratch=0;tested=0
 for length in cfg['patch_source_lengths']:
  starts=np.arange(0,start-length-max(cfg['patch_forecast_lags'])+1)
  if not len(starts):continue
  indices=np.rint(np.linspace(0,length-1,n)).astype(int)[None,:]+starts[:,None];Y=X[indices];scratch=max(scratch,Y.nbytes+indices.nbytes+X.nbytes+Q.nbytes)
  for shift in ([0] if absolute else cfg['patch_shifts']):
   bins=shift*2;ql=Q[:,:,max(bins,0):B+min(bins,0)];pl=Y[:,:,:,max(-bins,0):B-max(bins,0)]
   dot=np.sum(pl*ql[None,:,:,:],axis=-1);den=np.sqrt(np.sum(pl*pl,axis=-1)*np.sum(ql*ql,axis=-1)[None,:,:]);cos=np.divide(dot,den,out=np.zeros_like(dot),where=den>cfg['patch_floor']);cost=np.mean(1-cos,axis=(1,2));tested+=len(starts)
   for j in np.flatnonzero(cost<=cfg['patch_max_cost']):
    lo=int(starts[j]);hi=lo+length-1;future=[frames[hi+k]['pitch_readout'] for k in cfg['patch_forecast_lags']];future=[v for v in future if v is not None]
    if not future:continue
    ix=indices[j];energy=float(np.mean([abs(math.log(max(q[k]['channels']['s64']['rms'],1e-8)/max(frames[int(z)]['channels']['s64']['rms'],1e-8))) for k,z in enumerate(ix)]))
    candidates.append({'cost':float(cost[j]),'source_first_frame':lo,'source_last_frame':hi,'query_first_frame':start,'query_last_frame':end,'source_start_sample':frames[lo]['start_sample'],'source_end_sample':frames[hi]['end_sample'],'query_start_sample':q[0]['start_sample'],'query_end_sample':q[-1]['end_sample'],'pitch_shift':float(shift),'time_ratio':n/length,'spectral_difference':float(cost[j]),'energy_log_ratio_abs':energy,'timbre_changed':bool(cost[j]>=cfg['patch_timbre_threshold']),'coverage':1.,'prediction_pitch':float(np.median(future))+shift,'aligned_frame_indices':ix.tolist()})
 assert tested<=cfg['patch_max_candidates']
 candidates.sort(key=lambda z:(z['cost'],z['source_first_frame'],z['source_last_frame'],abs(z['pitch_shift']),z['pitch_shift']));chosen=[]
 for c in candidates:
  if all(c['source_last_frame']<a['source_first_frame'] or c['source_first_frame']>a['source_last_frame'] for a in chosen):chosen.append(c)
  if len(chosen)==2:break
 if not chosen:
  z=empty(anchor);z.update(search_candidate_count=tested,search_scratch_array_bytes=scratch);return z
 probs=[0.]*50;weights=[math.exp(-c['cost']/cfg['patch_temperature']) for c in chosen];sw=sum(weights)
 for c,w in zip(chosen,weights):
  delta=c['prediction_pitch']-anchor;m=[math.exp(-.5*((j-delta)/.08)**2) for j in range(-24,25)];sm=sum(m)
  if not sm:probs[-1]+=w/sw
  else:
   for j,v in enumerate(m):probs[j]+=w/sw*v/sm
 probs=[.999*v+.001/50 for v in probs];j=max(range(50),key=probs.__getitem__)
 return {'anchor_semitones':anchor,'probabilities':probs,'point_pitch_semitones':None if j==49 else anchor+j-24,'lookup_evidence':chosen,'search_candidate_count':tested,'search_scratch_array_bytes':scratch}

class Listener(old.Listener):
 def __init__(self,cfg):
  super().__init__(cfg);self.matrix=np.array(cfg['patch_filterbank']['weights']);self.patch_frames=[];self.patch_next=2048;self.status_records=[];self.missing_seen=False;self.patch_cache={};self.patch_compute={}
 def reset(self):
  super().reset();self.patch_frames=[];self.patch_next=self.total+2048;self.status_records=[];self.missing_seen=False;self.patch_cache={};self.patch_compute={}
 def missing(self,n):
  assert n==1024
  start=self.total;self.total+=n;self.reset();self.status_records.append({'start_sample':start,'end_sample':self.total,'status':'missing','pcm_sha256':None});self.missing_seen=True;self.patch_cache={};self.patch_compute={}
  # No imputation or feature synthesis. A discontinuity invalidates continuation.
  return {'status':'missing','features_generated':0,'forecast_available':False,'sample_count':n}
 def arrive(self,raw):
  assert not self.missing_seen,'A missing span requires explicit reset before resuming'
  self.patch_cache={};self.patch_compute={};z=super().arrive(raw)
  self.status_records.append({'start_sample':self.total-len(raw)//4,'end_sample':self.total,'status':'captured_silence' if not any(raw) else 'captured_samples','pcm_sha256':hashlib.sha256(raw).hexdigest()})
  active=['s64','s128'] if self.cfg['patch_development'] or self.cfg['selected_patch']=='multi' else ['s64']
  while self.patch_next<=self.total:
   end=self.patch_next;channels={}
   for k in active:
    sz=1024 if k=='s64' else 2048;rawpart=self.raw[(end-sz-self.offset)*4:(end-self.offset)*4];channels[k]={**feature(rawpart,self.matrix,self.cfg),'start_sample':end-sz,'end_sample':end,'wave_sha256':hashlib.sha256(rawpart).hexdigest()}
   block=self.raw[(end-1024-self.offset)*4:(end-self.offset)*4];pitch=accepted.periodicity(block,self.cfg['adapter'])['pitch_semitones']
   self.patch_frames.append({'start_sample':end-1024,'end_sample':end,'available_sample':self.total,'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'channels':channels,'pitch_readout':pitch});self.patch_next+=256
  assert len(self.patch_frames)<=self.cfg['patch_capacity'];return z
 def forecast(self):
  result=super().forecast();result['patch_frames']=self.patch_frames;result['capture_status']=self.status_records;result['patch_forecasts']={}
  for name in (['single','multi'] if self.cfg['patch_development'] else [self.cfg['selected_patch']]):
   if name in self.patch_cache:
    result['patch_forecasts'][name]=self.patch_cache[name];continue
   started=time.monotonic_ns();cfg={**self.cfg,'_active_channels':['s64'] if name=='single' else ['s64','s128']};hist=[{'observation':{'pitch_semitones':f['pitch_readout']}} for f in self.patch_frames];base=predict(hist,cfg)
   base['reference']=search(self.patch_frames,cfg);base['absolute']=search(self.patch_frames,cfg,True)
   if self.missing_seen:base={k:empty() for k in base}
   self.patch_cache[name]=base;self.patch_compute[name]=time.monotonic_ns()-started;result['patch_forecasts'][name]=base
  if self.missing_seen:result['forecasts']={front:{name:empty() for name in fs} for front,fs in result['forecasts'].items()}
  result['patch_readout_compute_ns']=self.patch_compute;result['missing_seen']=self.missing_seen;return result
