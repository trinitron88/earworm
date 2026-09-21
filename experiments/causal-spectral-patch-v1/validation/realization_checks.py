"""Additional saved-only realization/status checks of the predeclared invariants."""
import json,math,base64,hashlib,sys
from pathlib import Path
P=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(P));from records import read_lines
S=sys.argv[1];d=P/'data'/S;waves={x['episode']:x for x in map(json.loads,read_lines(d/'wave_archive.jsonl.gz'))};matches=0;statuses=0;maxerr=0.
for x in map(json.loads,read_lines(d/'cache.jsonl.gz')):
 p=x['operational'];raw=base64.b64decode(waves[x['episode']]['prefix_b64']);frames=p['patch_frames']
 for z in p['capture_status']:
  b=raw[z['start_sample']*4:z['end_sample']*4];assert hashlib.sha256(b).hexdigest()==z['pcm_sha256'];assert z['status']==('captured_silence' if not any(b) else 'captured_samples');statuses+=1
 for f in frames:
  for ch in f['channels'].values():assert math.isclose(sum(ch['band_power']),ch['power_sum'],abs_tol=1e-9,rel_tol=1e-12)
 for fs in p['patch_forecasts'].values():
  for name in ['reference','absolute']:
   for c in fs[name]['lookup_evidence']:
    query=frames[c['query_first_frame']:c['query_last_frame']+1];aligned=[frames[i] for i in c['aligned_frame_indices']];assert len(query)==len(aligned)==16
    energy=sum(abs(math.log(max(q['channels']['s64']['rms'],1e-8)/max(a['channels']['s64']['rms'],1e-8))) for q,a in zip(query,aligned))/len(query);error=abs(energy-c['energy_log_ratio_abs']);assert error<=1e-12 and c['spectral_difference']==c['cost'];maxerr=max(maxerr,error);matches+=1
out={'all_pass':True,'matches_checked':matches,'capture_status_records':statuses,'maximum_energy_residual_error':maxerr,'no_acoustic_model_calls':True,'scope':'Supplemental post-run implementation of already-frozen realization/capture preservation requirements; no criteria or source changes.'};(P/'validation'/f'realization_{S}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
