"""Causal, uncertainty-preserving within-event aggregation; frozen comparator fronts."""
import time,hashlib,json,math
import trim_front as frozen
accepted=frozen.accepted
observation=frozen.observation
predict=frozen.predict
NAMES=frozen.NAMES

def aggregate(windows,state,cfg):
    # No octave folding or expected-note snapping: separated acoustic clusters survive.
    valid=[];unknown=0.
    for w in windows:
        o=w['observation'];p=o['pitch_semitones'];hz=o['pitch_hz'];eligible=p is not None and hz*(w['end_sample']-w['start_sample'])/16000>=4
        if eligible:valid.append((p,max(.01,o['selected_periodicity'])))
        else:unknown+=1.
    clusters=[]
    for pitch,weight in sorted(valid):
        if clusters and pitch-clusters[-1]['min']<=cfg['aggregation_cluster_semitones']:
            c=clusters[-1];c['sum']+=pitch*weight;c['weight']+=weight;c['count']+=1
        else:clusters.append({'min':pitch,'sum':pitch*weight,'weight':weight,'count':1})
    clusters.sort(key=lambda c:(-c['weight'],c['min']));total=unknown+sum(c['weight'] for c in clusters)
    candidates=[{'pitch_semitones':c['sum']/c['weight'],'probability':c['weight']/total,'windows':c['count']} for c in clusters[:cfg['aggregation_top_candidates']]] if total else []
    unknown=1-sum(c['probability'] for c in candidates)
    if len(valid)<cfg['aggregation_min_valid'] or state is None:candidates=[];unknown=1.
    point=candidates[0]['pitch_semitones'] if candidates and candidates[0]['probability']>=.5 else None
    return {'candidates':candidates,'unknown_mass':max(0.,unknown),'point':point,'window_count':len(windows),'valid_count':len(valid),'cluster_count':len(clusters),'concentration':max([x['probability'] for x in candidates],default=0.),'disagreement':1-max([c['weight']/total for c in clusters],default=0.)}

def scenarios(events,cfg):
    # Exact product weights for retained all-known paths. Truncated/unknown mass is
    # explicitly unresolved, never renormalized into confident predictions.
    ev=list(events)
    while ev and ev[-1]['state_pitch'] is None:ev.pop()
    beam=[(1.,[])]
    for e in ev:
        candidates=e['distribution']['candidates'] if e['state_pitch'] is not None else [{'pitch_semitones':None,'probability':1.}]
        nxt=[(w*c['probability'],h+[c['pitch_semitones']]) for w,h in beam for c in candidates]
        nxt.sort(key=lambda z:-z[0]);beam=nxt[:cfg['mixture_beam']]
        if not beam:break
    return beam

def mixture(events,cfg):
    beam=scenarios(events,cfg);retained=sum(w for w,h in beam);anchor=round(beam[0][1][-1]) if beam and beam[0][1] and beam[0][1][-1] is not None else None
    paths=[(w,predict([{'observation':{'pitch_semitones':p}} for p in h],cfg)) for w,h in beam]
    out={}
    for name in NAMES:
        probs=[0.]*50;probs[-1]=max(0.,1-retained)
        if anchor is None:probs=[0.]*49+[1.]
        else:
            for weight,forecasts in paths:
                f=forecasts[name]
                for j,mass in enumerate(f['probabilities']):
                    k=49 if j==49 or f['anchor_semitones'] is None else round(f['anchor_semitones']+j-24)-anchor+24
                    probs[k if 0<=k<49 else 49]+=weight*mass
        mode=max(range(50),key=probs.__getitem__)
        out[name]={'probabilities':probs,'anchor_semitones':anchor,'point_pitch_semitones':None if mode==49 or anchor is None else anchor+mode-24,'lookup_evidence':[],'retained_history_mass':retained,'unresolved_history_mass':max(0.,1-retained),'history_paths':len(beam),'probability_note':'Frozen interval coordinates around integer acoustic anchor; candidate path absolute predictions rounded to same scoring bins. Out-of-range and unresolved mass unknown.'}
    return out

class Listener(frozen.Listener):
    def __init__(self,cfg):
        super().__init__(cfg);self.aggregates={p['id']:[] for p in cfg['aggregation_grid'] if cfg['aggregation_development'] or p['id']==cfg['selected_aggregation']};self.window_calls=0
    def reset(self):
        super().reset();self.aggregates={p['id']:[] for p in self.cfg['aggregation_grid'] if self.cfg['aggregation_development'] or p['id']==self.cfg['selected_aggregation']}
    def arrive(self,raw):
        result=super().arrive(raw);originals=self.fronts[self.cfg['selected']].events
        for policy in self.cfg['aggregation_grid']:
            key=policy['id']
            if key not in self.aggregates:continue
            for idx in range(len(self.aggregates[key]),len(originals)):
                orig=originals[idx];windows=[]
                for size in policy['windows']:
                    for lo in range(orig['start_sample']+policy['edge'],orig['end_sample']-policy['edge']-size+1,policy['hop']):
                        hi=lo+size;block=self.raw[(lo-self.offset)*4:(hi-self.offset)*4];o=observation(block,self.cfg);self.window_calls+=1
                        windows.append({'start_sample':lo,'end_sample':hi,'available_sample':self.total,'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'observation':o})
                dist=aggregate(windows,orig['state_pitch'],self.cfg);point=dist['point'];obs={**orig['observation'],'pitch_semitones':point,'pitch_hz':None if point is None else 220*2**(point/12),'pitch_available':point is not None,'interpretation':'MAP consensus; original observation stored separately'}
                self.aggregates[key].append({**orig,'available_sample':self.total,'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'observation':obs,'original_event_index':idx,'original_observation_sha256':hashlib.sha256(json.dumps(orig['observation'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'windows':windows,'distribution':dist})
        return result
    def forecast(self):
        result=super().forecast()
        for key,ev in self.aggregates.items():
            result['events'][key]=ev;result['forecasts'][key]=predict(ev,self.cfg)
            result['events'][key+'_mixture']=ev;result['forecasts'][key+'_mixture']=mixture(ev,self.cfg)
        result['aggregation_policies_active']=list(self.aggregates);result['aggregation_window_calls']=self.window_calls
        return result
