"""Independent scalar reconstruction using saved measurements, no extraction."""
import math

def distribution(ws,state,cfg):
 points=[];bad=0
 for w in ws:
  o=w['observation'];p=o['pitch_semitones']
  if p is None or o['pitch_hz']*(w['end_sample']-w['start_sample'])/16000<4:bad+=1
  else:points.append((p,max(.01,o['selected_periodicity'])))
 clusters=[]
 for p,w in sorted(points):
  if not clusters or p-clusters[-1][0][0]>.35:clusters.append([])
  clusters[-1].append((p,w))
 total=bad+sum(w for p,w in points);clusters.sort(key=lambda c:(-sum(w for p,w in c),c[0][0]));cs=[]
 if state is not None and len(points)>=2:
  for c in clusters[:2]:
   weight=sum(w for p,w in c);cs.append({'pitch_semitones':sum(p*w for p,w in c)/weight,'probability':weight/total,'windows':len(c)})
 unknown=max(0.,1-sum(c['probability'] for c in cs));point=cs[0]['pitch_semitones'] if cs and cs[0]['probability']>=.5 else None
 return cs,unknown,point

def mix(events,cfg,name,reconstruct):
 ev=list(events)
 while ev and ev[-1]['state_pitch'] is None:ev.pop()
 beam=[(1.,[])]
 for e in ev:
  options=[(None,1.)] if e['state_pitch'] is None else [(v['pitch_semitones'],v['probability']) for v in e['distribution']['candidates']]
  beam=sorted([(w*v,h+[p]) for w,h in beam for p,v in options],key=lambda z:-z[0])[:16]
 mass=sum(w for w,h in beam);anchor=round(beam[0][1][-1]) if beam and beam[0][1] and beam[0][1][-1] is not None else None;p=[0.]*49+[max(0.,1-mass)]
 if anchor is None:return [0.]*49+[1.],None
 for weight,h in beam:
  while h and h[-1] is None:h=h[:-1]
  mc=dict(cfg['reference']);source=name
  if name.startswith('transition'):source='transition';mc['transition_order']=int(name[-1])
  elif name=='absolute':source='retrieval_absolute';mc['retrieval_absolute_order']=3
  elif name=='reference':source='retrieval_transposed'
  pp,_,_=reconstruct([{'pitch_semitones':v} for v in h] or [{'pitch_semitones':None}],source,mc)
  for j,v in enumerate(pp):
   k=round(h[-1]+j-24)-anchor+24 if j<49 and h and h[-1] is not None else 49;p[k if 0<=k<49 else 49]+=weight*v
 mode=max(range(50),key=p.__getitem__);return p,None if mode==49 else anchor+mode-24
