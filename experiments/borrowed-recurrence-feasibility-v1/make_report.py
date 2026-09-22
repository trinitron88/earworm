"""Saved-only human report and realization evidence; no listening/model execution."""
import csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def main(split):
 d=ROOT/'results'/split;a=json.loads((d/'analysis.json').read_text());r=a['resource'];rows=[]
 def fmt(x):return 'unavailable' if x is None else f'{100*x:.1f}%'
 def ci(m):return fmt(m['value'])+' ['+', '.join(fmt(x) for x in m['ci95'])+']'
 lines=['# Borrowed recurrence feasibility — '+split,'',f"**Decision {a['decision']}.** {a['reason']}",'',f"Selected MERT candidate: {a['selected_mert']}. Selected adequate audio route: {a['selected_route'] or 'none'}.",'','These are isolated rendered Bach score figures and newly composed motifs. Construction correspondence is not human perceptual identity. Each source occurred once, followed by 32 seconds of intervening music and actual eviction from the four-second raw buffer. Query selection uses the last two seconds of observed sound; source/query boundaries and note labels never enter the audio listener.','', '| Route | Unchanged identity | Transposed identity | Stretched identity | Foil false acceptance | Qualifies |','|---|---:|---:|---:|---:|---|']
 for route,data in a['routes'].items():
  full=data['conditions']['full']
  vals=[ci(full[c]['all']['metrics']['correct_identity']) for c in ('unchanged','transpose','stretch')]+[ci(full['foil']['all']['metrics']['false_accept'])]
  lines.append('| '+route+' | '+' | '.join(vals)+f" | {data['qualifies']} |")
 lines+=['','Brackets are paired-family bootstrap 95% intervals, not population guarantees. Full metrics by cell, stratum and memory condition are in `analysis.json`; intervals crossing acceptance thresholds remain visible.','', '## Transformation and memory benefit','', '| Route | Joint transposition | Joint stretch | Full − recent identity | Full − source removal identity |','|---|---:|---:|---:|---:|']
 for route,data in a['routes'].items():
  f=data['conditions']['full'];h=data['history_benefit'];vals=[ci(f[c]['all']['metrics']['joint_correct']) for c in ('transpose','stretch')]+[ci(h[c]['all']['identity']) for c in ('recent','removed')]
  lines.append('| '+route+' | '+' | '.join(vals)+' |')
 lines+=['','## Evidence, preservation and limits','',f"Validation checks: `{json.dumps(a['checks'],sort_keys=True)}`.",'',f"Conservatively charged executions/probes: {r['executions']}/1000, including {r['actual_music_readouts']} actual music readouts and a 40-probe qualification charge. Aggregate compute charge: {r['aggregate_compute_seconds']:.1f}/7200 seconds. Package files at analysis: {r['new_artifact_bytes']:,} bytes; spending $0. Source download: 123,847 bytes. Publication accounting is saved separately.",'',f"Peak listener RSS: {r['peak_listener_rss_bytes']:,} bytes, including fixed encoder, transient work and state. There was **no FIFO capacity pressure**; this is delay/interference retention under a cap, not demonstrated resistance to replacement.",'','The MERT route is a hybrid: correspondence uses frozen MERT features, while shift estimation uses the shared acoustic sidecar. The standard route is a disclosed FFT/trailing-smoothing CENS variant with the FMP unweighted step-skipping DTW. Failure can reflect the limited query window, observation features, alignment or rejection; it does not prove an encoder contains no musical relationships.','', '| Route | Max latency (s) | Max RTF | Persistent bytes (upper bound) |','|---|---:|---:|---:|']
 for route,rr in r['routes'].items():lines.append(f"| {route} | {rr['max_decision_latency_seconds']:.4f} | {rr['extraction_matching_rtf']:.4f} | {rr['peak_persistent_bytes']:,} |")
 lines+=['','Failed gates:','']
 for route,data in a['routes'].items():lines.append(f"- **{route}:** "+(', '.join(data['failed_gates']) or 'none'))
 lines+=['','Invalid reasons: '+('; '.join(a['invalid_reasons']) or 'none')+'.','Missing evidence: '+('; '.join(a['missing_evidence']) or 'none')+'.','','## Absolute realization evidence','', 'The following saved table retains absolute spectral register, energy and timing beside invariant lookup. Spectral-register centroid is power-weighted on the logarithmic frequency axis; it is not a fundamental-pitch estimate. Frame summaries weight actual overlap duration with each construction interval. These values do not determine acceptance. Full timestamped bins, including source evidence after raw-audio eviction, remain in every `measurements.npz`.','', '| Cell | Mean spectral-centroid change (semitone units) | Mean RMS ratio | Mean query/source duration |','|---|---:|---:|---:|']
 summaries=json.loads((d/'summaries.json').read_text())
 for s in summaries:
  p=d/(s['group']+'-'+s['cell']);labels=json.loads((p/'labels.json').read_text())
  with np.load(p/'measurements.npz') as z:
   t=z['t'];power=z['power'];rms=z['rms'];m=[]
   for start,end in ((labels['source_onset'],labels['source_offset']),(labels['query_onset'],labels['query_offset'])):
    w=np.maximum(0,np.minimum(t+.05,end)-np.maximum(t-.05,start));v=(power*w[:,None]).sum(0)/w.sum()
    m.append({'spectral_centroid_midi_units':float(np.dot(v,np.arange(24,105))/sum(v)),'absolute_rms':float(np.sqrt(np.dot(w,rms*rms)/sum(w))),'duration_seconds':end-start,'covered_seconds':float(sum(w))})
   rows.append({'group':s['group'],'cell':s['cell'],'source':m[0],'query':m[1],'register_difference':m[1]['spectral_centroid_midi_units']-m[0]['spectral_centroid_midi_units'],'rms_ratio':m[1]['absolute_rms']/m[0]['absolute_rms'],'duration_ratio':m[1]['duration_seconds']/m[0]['duration_seconds']})
 for cell in ('unchanged','transpose','stretch','foil'):
  rr=[x for x in rows if x['cell']==cell];vals=[np.mean([x[k] for x in rr]) for k in ('register_difference','rms_ratio','duration_ratio')]
  lines.append(f'| {cell} | '+ ' | '.join(f'{v:.4f}' for v in vals)+' |')
 lines+=['','Signed transposition averages can cancel because shifts are balanced; consult each family in `realization-evidence.json` to see the retained change.','', '## Review and next action','', 'Review the exact publication head and execution freeze, saved predictions committed before labels, archived inputs/measurements, independent validation, all negative outcomes and resource ledger. Stop for the existing reviewer’s A/B/C/INVALID disposition. No automatic repair, new experiment, controller, training or paid compute follows this report.','']
 (d/'realization-evidence.json').write_text(json.dumps(rows,indent=2)+'\n');(d/'REPORT.md').write_text('\n'.join(lines))
if __name__=='__main__':main(sys.argv[1])
