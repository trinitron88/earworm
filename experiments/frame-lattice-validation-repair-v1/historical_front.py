"""Causal event formation; only arrived PCM and immutable configuration."""
import numpy as np,hashlib,time
import accepted_adapter as accepted
import reference_model as ref
NAMES=['present','recency','transition1','transition2','transition3','absolute','reference']
def predict(events,cfg):
    h=[e['observation'] for e in events]
    while h and h[-1]['pitch_semitones'] is None:h.pop()
    out={}
    for name in NAMES:
        c=dict(cfg['reference']);source=name
        if name.startswith('transition'):source='transition';c['transition_order']=int(name[-1])
        elif name=='absolute':source='retrieval_absolute';c['retrieval_absolute_order']=3
        elif name=='reference':source='retrieval_transposed'
        f=ref.forecast(h,c)[source];f['lookup_evidence']=ref.candidates(h,source,c);out[name]=f
    return out

def observation(raw,cfg):
    original=ref.observe(raw);rep=accepted.periodicity(raw,cfg['adapter']);return {**original,**rep,'original_spectral_peak':original,'wave_sha256':hashlib.sha256(raw).hexdigest()}

class Boundary:
    def __init__(self,params,cfg):self.params=params;self.cfg=cfg;self.events=[];self.start=0;self.label=None;self.pending=[]
    def step(self,frame,raw,offset):
        p=frame['pitch_semitones'];same=(p is None and self.label is None) or (p is not None and self.label is not None and abs(p-self.label)<self.params['pitch_change'])
        if same:self.pending=[];return
        if self.pending:
            old=self.pending[-1]['pitch_semitones'];consistent=(p is None and old is None) or (p is not None and old is not None and abs(p-old)<self.params['pitch_change'])
            if not consistent:self.pending=[]
        self.pending.append(frame);required=8 if p is None else self.params['confirm']
        if len(self.pending)<required:return
        first=self.pending[0];split=max(self.start,first['end_sample']-self.cfg['window_samples']//2)
        if split-self.start>=256:
            segment=raw[(self.start-offset)*4:(split-offset)*4];obs=observation(segment,self.cfg)
            if self.label is None:obs={**obs,'unmasked_observation':obs,'pitch_semitones':None,'pitch_hz':None,'pitch_available':False}
            self.events.append({'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'state_pitch':self.label,'start_sample':self.start,'end_sample':split,'available_sample':frame['end_sample'],'observation':obs})
            assert len(self.events)<=32
        self.start=split;self.label=p;self.pending=[]

class Listener:
    def __init__(self,cfg):
        self.cfg=cfg;self.offset=0;self.total=0;self.raw=b'';self.next_frame=cfg['window_samples'];self.frames=[];self.fixed=[];self.fronts={q['id']:Boundary(q,cfg) for q in cfg['boundary_grid'] if cfg['development_grid'] or q['id']==cfg['selected']};self.resets=0;self.hashes=[];self.chunk_count=0
    def reset(self):
        self.offset=self.total;self.raw=b'';self.next_frame=self.total+self.cfg['window_samples'];self.frames=[];self.fixed=[];self.fronts={q['id']:Boundary(q,self.cfg) for q in self.cfg['boundary_grid'] if self.cfg['development_grid'] or q['id']==self.cfg['selected']}
        for f in self.fronts.values():f.start=self.total
        self.resets+=1
    def arrive(self,raw):
        assert len(raw)==self.cfg['chunk_samples']*4
        start=self.total;self.total+=len(raw)//4;self.raw+=raw;self.hashes.append(hashlib.sha256(raw).hexdigest());self.chunk_count+=1
        assert self.chunk_count<=32 and len(self.raw)<=2*16000*4
        fixed_observation=observation(raw,self.cfg)
        self.fixed.append({'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns(),'start_sample':start,'end_sample':self.total,'available_sample':self.total,'observation':fixed_observation})
        assert len(self.fixed)<=32
        while self.next_frame<=self.total:
            end=self.next_frame;block=self.raw[(end-self.offset-self.cfg['window_samples'])*4:(end-self.offset)*4];a=accepted.periodicity(block,self.cfg['adapter']);f={'start_sample':end-self.cfg['window_samples'],'end_sample':end,'available_sample':self.total,'pitch_semitones':a['pitch_semitones'],'periodicity':a['selected_periodicity'],'rms':a['rms'],'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns()};self.frames.append(f)
            for front in self.fronts.values():front.step(f,self.raw,self.offset)
            self.next_frame+=self.cfg['hop_samples']
        return {'arrived_samples':self.total,'chunk_count':self.chunk_count,'event_counts':{k:len(v.events) for k,v in self.fronts.items()},'evictions':0}
    def forecast(self):
        # available_sample of decision must include chunk completion, not backdated frame end.
        outputs={};events={}
        for key,front in self.fronts.items():
            ev=[{**e,'available_sample':((e['available_sample']+self.cfg['chunk_samples']-1)//self.cfg['chunk_samples'])*self.cfg['chunk_samples']} for e in front.events]
            events[key]=ev;outputs[key]=predict(ev,self.cfg)
        events['fixed']=self.fixed;outputs['fixed']=predict(self.fixed,self.cfg)
        return {'forecasts':outputs,'events':events,'frames':self.frames,'arrived_samples':self.total,'chunk_count':self.chunk_count,'resets':self.resets,'evictions':0,'raw_buffer_samples':len(self.raw)//4,'raw_buffer_sha256':hashlib.sha256(self.raw).hexdigest(),'chunk_hashes':self.hashes,'capacity_events_per_front':32,'buffer_offset':self.offset}
