"""Evaluator-only source labels; transformation outputs scored separately."""
def assess(f,t):
 b=f['lookup_evidence'][0] if f['lookup_evidence'] else None;source=False;err=None
 if b:
  for r in t['source_regions']:
   overlap=max(0,min(r['end'],b['source_end_sample'])-max(r['start'],b['source_start_sample']));e=abs(b['source_end_sample']-r['end'])/16000
   if overlap/max(1,b['source_end_sample']-b['source_start_sample'])>=.8 and e<=.064:source=True;err=e
 return {'source_accuracy':float(source),'false_match':float(b is not None) if t['unrelated'] else 0.,'rejection':float(b is None),'pitch_accuracy':float(b is not None and abs(b['pitch_shift']-t['expected_pitch_shift'])<=.5),'time_accuracy':float(b is not None and abs(b['time_ratio']-t['expected_time_ratio'])<=.10),'timbre_accuracy':float(b is not None and b['timbre_changed']==t['expected_timbre_changed']),'alignment_coverage':b['coverage'] if b else 0.,'alignment_end_error':err,'pitch_shift':b['pitch_shift'] if b else None,'time_ratio':b['time_ratio'] if b else None,'spectral_residual':b['spectral_difference'] if b else None,'energy_residual':b['energy_log_ratio_abs'] if b else None}
