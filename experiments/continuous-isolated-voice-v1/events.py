"""Evaluator-only time correspondence. Never imported by operational worker."""
import numpy as np

def event_metrics(events,truth,reset_sample=None):
    ts=[t for t in truth if t['pitch'] is not None and (reset_sample is None or t['start']>=reset_sample)]
    ps=[e for e in events if e.get('state_pitch',e['observation']['pitch_semitones']) is not None]
    candidates=[]
    for i,p in enumerate(ps):
      for j,t in enumerate(ts):
        intersection=max(0,min(p['end_sample'],t['end'])-max(p['start_sample'],t['start']));union=max(p['end_sample'],t['end'])-min(p['start_sample'],t['start'])
        if intersection and intersection/union>=.5:candidates.append((intersection/union,i,j))
    matches=[];usedp=set();usedt=set()
    for _,i,j in sorted(candidates,reverse=True):
        if i in usedp or j in usedt:continue
        usedp.add(i);usedt.add(j);matches.append((i,j))
    bounded=[(i,j) for i,j in matches if abs(ps[i]['start_sample']-ts[j]['start'])<=400 and abs(ps[i]['end_sample']-ts[j]['end'])<=400]
    tp=len(bounded);precision=tp/len(ps) if ps else 0.;recall=tp/len(ts) if ts else 0.;f1=2*tp/(len(ps)+len(ts)) if ps or ts else 1.
    split=sum(sum(max(0,min(p['end_sample'],t['end'])-max(p['start_sample'],t['start']))>=.2*(t['end']-t['start']) for p in ps)>1 for t in ts)
    merge=sum(sum(max(0,min(p['end_sample'],t['end'])-max(p['start_sample'],t['start']))>=.2*(t['end']-t['start']) for t in ts)>1 for p in ps)
    correct=available=octave=0;errors=[];onsets=[];ends=[];latencies=[]
    for i,j in matches:
        p,t=ps[i],ts[j];q=p['observation']['pitch_semitones'];available+=q is not None
        if q is not None:errors.append(abs(q-t['pitch']));correct+=abs(q-t['pitch'])<=.35;octave+=abs(abs(q-t['pitch'])-12)<=.35
        onsets.append(abs(p['start_sample']-t['start'])/16000);ends.append(abs(p['end_sample']-t['end'])/16000);latencies.append((p['available_sample']-t['end'])/16000)
    return dict(true_events=len(ts),predicted_events=len(ps),matched_events=len(matches),bounded_matches=tp,precision=precision,recall=recall,f1=f1,split_count=int(split),merge_count=int(merge),split_rate=split/max(1,len(ts)),merge_rate=merge/max(1,len(ts)),pitch_accuracy=correct/max(1,len(ts)),pitch_availability=available/max(1,len(ts)),mean_pitch_error_available=float(np.mean(errors)) if errors else None,octave_error_rate=octave/max(1,len(ts)),mean_onset_error_s=float(np.mean(onsets)) if onsets else None,mean_end_error_s=float(np.mean(ends)) if ends else None,max_true_end_latency_s=max(latencies,default=0.),max_inferred_end_latency_s=max(((p['available_sample']-p['end_sample'])/16000 for p in ps),default=0.),matches=[{'predicted':i,'truth':j} for i,j in matches])
