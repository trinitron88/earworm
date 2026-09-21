"""Independent saved-patch search enumeration and probability arithmetic."""
import numpy as np,statistics,math

def reconstruct(frames,cfg,channels,absolute=False):
 active=[i for i,x in enumerate(frames) if x['channels']['s64']['rms']>=cfg['patch_silence_rms']]
 if not active:return [0.]*49+[1.],None,[]
 last=active[-1];first=last-15
 if first<0:return [0.]*49+[1.],None,[]
 pitches=[x['pitch_readout'] for x in frames[first:last+1] if x['pitch_readout'] is not None]
 if not pitches:return [0.]*49+[1.],None,[]
 anchor=pitches[-1];candidates=[];features={k:np.array([f['channels'][k]['identity'] for f in frames]) for k in channels}
 for length in cfg['patch_source_lengths']:
  starts=list(range(first-length-max(cfg['patch_forecast_lags'])+1))
  if not starts:continue
  offsets=[round(i*(length-1)/15) for i in range(16)];ix=np.array([[s+i for i in offsets] for s in starts])
  for semitones in ([0] if absolute else cfg['patch_shifts']):
   shift=2*semitones;scores=np.zeros(len(starts))
   for name in channels:
    a=features[name][first:last+1];b=features[name][ix]
    if shift>0:a=a[:,shift:];b=b[:,:,:-shift]
    elif shift<0:a=a[:,:shift];b=b[:,:,-shift:]
    products=np.sum(a[None,:,:]*b,axis=2);norm=np.sqrt(np.sum(a*a,axis=1)[None,:]*np.sum(b*b,axis=2));sim=np.divide(products,norm,out=np.zeros_like(products),where=norm>cfg['patch_floor']);scores+=np.mean(1-sim,axis=1)/len(channels)
   for s,cost in zip(starts,scores):
    hi=s+length-1;future=[frames[hi+lag]['pitch_readout'] for lag in cfg['patch_forecast_lags']];future=[x for x in future if x is not None]
    if cost<=cfg['patch_max_cost'] and future:candidates.append((float(cost),s,hi,abs(semitones),semitones,statistics.median(future)+semitones))
 candidates.sort();selected=[]
 for c in candidates:
  if all(c[2]<a[1] or c[1]>a[2] for a in selected):selected.append(c)
  if len(selected)==2:break
 if not selected:return [0.]*49+[1.],None,[]
 weights=[math.exp(-c[0]/cfg['patch_temperature']) for c in selected];total=sum(weights);p=[0.]*50
 for c,w in zip(selected,weights):
  delta=c[5]-anchor;mass=[math.exp(-.5*((j-delta)/.08)**2) for j in range(-24,25)];sm=sum(mass)
  if sm:
   for j,v in enumerate(mass):p[j]+=w/total*v/sm
  else:p[-1]+=w/total
 p=[.999*v+.001/50 for v in p];k=max(range(50),key=p.__getitem__)
 return p,None if k==49 else anchor+k-24,selected
