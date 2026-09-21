"""Append interior-support measurements; historical event formation unchanged."""
import time,hashlib,json
import historical_front as frozen
accepted=frozen.accepted
observation=frozen.observation
predict=frozen.predict
NAMES=frozen.NAMES
class Listener(frozen.Listener):
    def __init__(self,cfg):
        super().__init__(cfg);self.support_calls=0;self.supports={p['id']:[] for p in cfg['support_grid'] if cfg['support_development'] or p['id']==cfg['selected_support']}
    def reset(self):
        super().reset();self.supports={p['id']:[] for p in self.cfg['support_grid'] if self.cfg['support_development'] or p['id']==self.cfg['selected_support']}
    def arrive(self,raw):
        result=super().arrive(raw);events=self.fronts[self.cfg['selected']].events
        for policy in self.cfg['support_grid']:
            key=policy['id']
            if key not in self.supports:continue
            for idx in range(len(self.supports[key]),len(events)):
                e=events[idx];lo=e['start_sample']+policy['trim_samples'];hi=e['end_sample']-policy['trim_samples'];sufficient=hi-lo>=self.cfg['min_support_samples'];reason=None
                if sufficient:
                    crop=self.raw[(lo-self.offset)*4:(hi-self.offset)*4];self.support_calls+=1;obs=observation(crop,self.cfg);hz=obs['pitch_hz'];cycles=(hi-lo)/16000*hz if hz is not None else None
                    if cycles is None or cycles<self.cfg['min_support_cycles']:reason='insufficient periodic evidence or cycles';sufficient=False
                    if e['state_pitch'] is None:reason='unpitched boundary state';sufficient=False
                    candidate={'pitch_hz':obs['pitch_hz'],'pitch_semitones':obs['pitch_semitones'],'selected_periodicity':obs['selected_periodicity']}
                    if not sufficient:obs={**obs,'candidate_before_availability_gate':candidate,'pitch_hz':None,'pitch_semitones':None,'pitch_available':False,'support_gate_reason':reason}
                    support=dict(start_sample=lo,end_sample=hi,duration_s=(hi-lo)/16000,wave_sha256=hashlib.sha256(crop).hexdigest(),cycles=cycles,meets_min_duration=True)
                else:
                    obs={**e['observation'],'pitch_hz':None,'pitch_semitones':None,'pitch_available':False,'support_gate_reason':'inferred span too short for trim and32ms support'};support=None;reason=obs['support_gate_reason']
                self.supports[key].append({'start_sample':e['start_sample'],'end_sample':e['end_sample'],'whole_event_duration_s':(e['end_sample']-e['start_sample'])/16000,'state_pitch':e['state_pitch'],'original_event_index':idx,'original_front':self.cfg['selected'],'original_observation_sha256':hashlib.sha256(json.dumps(e['observation'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'support':support,'measurement_available':sufficient,'unavailable_reason':reason,'observation':obs,'available_sample':self.total,'computed_monotonic_ns':time.monotonic_ns(),'computed_utc_ns':time.time_ns()})
        return result
    def forecast(self):
        result=super().forecast()
        for key,events in self.supports.items():result['events'][key]=events;result['forecasts'][key]=predict(events,self.cfg)
        result['support_policies_active']=list(self.supports);result['support_observation_calls']=self.support_calls
        return result
