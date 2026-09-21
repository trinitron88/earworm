"""Saved-only independent features, patch search, forecasts, capture status and provenance."""
from pathlib import Path
import json,hashlib,base64,math,sys
import numpy as np
from records import read_lines
import baseline_validation as baseline
from scoring import measure,safe
from validation.patch_arithmetic import reconstruct as patch_reconstruct
P=Path(__file__).resolve().parent
def h(b):return hashlib.sha256(b).hexdigest()
def main(split):
 baseline.main(split)
 d=P/'data'/split;cfg=json.loads((d/'config_used.json').read_text());truth={v['episode']:v for v in map(json.loads,read_lines(d/'truth.jsonl.gz'))};waves={v['episode']:v for v in map(json.loads,read_lines(d/'wave_archive.jsonl.gz'))};records=[v['record'] for v in map(json.loads,read_lines(d/'events.jsonl.gz'))];by={}
 for r in records:by.setdefault(r['episode'],[]).append(r)
 fb=cfg['patch_filterbank'];edges=np.array(fb['edges_hz']);frequencies=np.arange(2049)*16000/4096;weights=[]
 for lo,hi in zip(edges[:-1],edges[1:]):
  row=np.array([max(0.,min(hi,f+16000/8192)-max(lo,f-16000/8192)) for f in frequencies]);weights.append(row/row.sum())
 weights=np.array(weights);assert np.max(abs(weights-np.array(fb['weights'])))<=1e-12
 prior=json.loads((P/'prior_wave_hashes.json').read_text());prior_full=set(prior['full_waveforms']);prior_units=set(prior['non_silent_units']);count=0;features=0;maxerror=0.;maxfeature=0.;probe_count=0
 for x in map(json.loads,read_lines(d/'cache.jsonl.gz')):
  eid=x['episode'];t=truth[eid];pred=x['operational'];raw=base64.b64decode(waves[eid]['prefix_b64']);rs=by[eid];q=next(r for r in rs if r['kind']=='query_commit');fc=next(r for r in rs if r['kind']=='forecast_commit');gen=next(r for r in rs if r['kind']=='target_generated_after_commit');assert q['seq']<fc['seq']<gen['seq'] and q['prefix_sha256']==h(raw);assert gen['future_sha256']==h(base64.b64decode(waves[eid]['future_b64']))
  dispatch={r['offset']:r['monotonic_ns'] for r in rs if r['kind']=='chunk_dispatch'};arrival={r['offset']:r['monotonic_ns'] for r in rs if r['kind']=='arrival'};offset=t['reset_sample'] or 0
  assert [f['end_sample'] for f in pred['patch_frames']]==list(range(offset+2048,len(raw)//4+1,256));assert len(pred['patch_frames'])<=128
  for f in pred['patch_frames']:
   ch=(f['available_sample']//1024-1)*1024;assert dispatch[ch]<=f['computed_monotonic_ns']<=arrival[ch]
   for name,z in f['channels'].items():
    n=1024 if name=='s64' else 2048;assert z['end_sample']==f['end_sample'] and z['start_sample']==f['end_sample']-n;block=raw[z['start_sample']*4:z['end_sample']*4];assert h(block)==z['wave_sha256'];samples=np.frombuffer(block,dtype='<f4').astype(float);power=abs(np.fft.rfft(samples*np.hanning(n),n=4096))**2
    bands=np.array([np.sum(row*power) for row in weights]);total=float(bands.sum());v=np.log1p(cfg['patch_log_gain']*bands/max(total,cfg['patch_floor']));v/=max(float(np.sqrt(np.sum(v*v))),cfg['patch_floor']);rms=float(np.sqrt(np.mean(samples*samples)))
    assert np.allclose(bands,z['band_power'],rtol=1e-12,atol=1e-9);err=float(np.max(abs(v-z['identity'])));assert err<=1e-12 and abs(rms-z['rms'])<=1e-12;assert z['status']==('captured_silence' if rms<.01 else 'captured_sound');maxfeature=max(maxfeature,err);features+=1
  assert h(raw) not in prior_full and h(base64.b64decode(waves[eid]['future_b64'])) not in prior_full
  assert not ({b['wave_sha256'] for b in t['bounds'] if b['pitch'] is not None}&prior_units)
  scores=next(r for r in rs if r['kind']=='score')['scores']
  for front,fs in pred['patch_forecasts'].items():
   channels=['s64'] if front=='single' else ['s64','s128']
   hist=[{'pitch_semitones':f['pitch_readout']} for f in pred['patch_frames']]
   for name,f in fs.items():
    if name in ['reference','absolute']:
     probs,point,cs=patch_reconstruct(pred['patch_frames'],cfg,channels,name=='absolute');assert len(cs)==len(f['lookup_evidence'])
     for a,b in zip(cs,f['lookup_evidence']):
      assert a[1:3]==(b['source_first_frame'],b['source_last_frame']) and a[4]==b['pitch_shift'];assert abs(a[0]-b['cost'])<=1e-12 and abs(a[5]-b['prediction_pitch'])<=1e-12
      assert b['time_ratio']==16/(b['source_last_frame']-b['source_first_frame']+1);assert b['timbre_changed']==(b['spectral_difference']>=cfg['patch_timbre_threshold'])
    else:
     mc=dict(cfg['reference']);source=name
     if name.startswith('transition'):mc['transition_order']=int(name[-1]);source='transition'
     hh=hist.copy()
     while hh and hh[-1]['pitch_semitones'] is None:hh.pop()
     probs,point,_=baseline.reconstruct(hh or [{'pitch_semitones':None}],source,mc)
    err=max(abs(a-b) for a,b in zip(probs,f['probabilities']));assert err<=1e-12;assert point==f['point_pitch_semitones'] or point is not None and f['point_pitch_semitones'] is not None and abs(point-f['point_pitch_semitones'])<=1e-12;assert baseline.numerical_equal(safe(measure(f,t)),scores['patch-'+front][name]);maxerror=max(maxerror,err);count+=1
  assert not pred['missing_seen'] and all(z['pcm_sha256'] is not None for z in pred['capture_status'])
  for r in rs:
   if r['kind']=='silence_missing_probe':
    assert r['silence_status']=='captured_silence' and r['missing_status']['status']=='missing' and r['missing_status']['pcm_sha256'] is None and r['missing_response']['features_generated']==0 and r['missing_forecasts_unknown'] and r['restored_original_bytes'];probe_count+=1
 assert probe_count==len({t['group'] for t in truth.values()})
 result={'all_pass':True,'baseline_validation':'baseline_'+split+'.json','patch_forecasts':count,'spectral_channel_frames':features,'maximum_identity_error':maxfeature,'maximum_forecast_error':maxerror,'silence_missing_probes':probe_count,'query_committed_before_retrieval':True,'future_generation_after_commit':True,'raw_identity_realization_preserved':True,'independent_full_search':True,'tolerance':'Band power abs1e-9 plus relative1e-12; identity/RMS/forecast1e-12; hashes exact.'}
 (P/'validation'/f'{split}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main(sys.argv[1])
