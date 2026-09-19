"""Experiment08: waveform-derived evidence, competing alignments, explicit uncertainty.

No labels, phrase IDs, generator parameters, or expected edit types enter this
module. Its input descriptions are retained unchanged. Support logits are not
probabilities. Alignment and evidence rules are engineered, not discovered.
"""
from __future__ import annotations
import hashlib
import numpy as np
from remember_changes_acoustics import equal_bins

PARAMETERS = dict(min_phase_fraction=.5, max_pitch_span_cents=150.,
    max_centroid_f0_ratio=4., gap_cost=.7, pitch_scale_semitones=2.,
    pitch_deadzone_semitones=.05, timing_deadzone_s=.005,
    timing_cost_per_second=2., initial_normalized_timing_weight=.15,
    shift_proposals=8, paths_per_cell=2, max_retained_paths=4,
    retained_cost_slack=.15, quiet_relative_rms=.01, quiet_absolute_rms=1e-5,
    pitch_edit_reporting_semitones=.2, timing_edit_reporting_s=.015)
FEATURE_NAMES = ['cost','matched_log','reference_coverage','query_coverage',
    'mean_pitch_loss','exact_pitch_fraction','mean_timing_loss',
    'missing_fraction','inserted_fraction','unreliable_query_fraction',
    'reference_log','query_log']

def description_digest(d):
    h=hashlib.sha256()
    for k in sorted(d):
        a=np.asarray(d[k]);h.update(k.encode());h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()

def events(d):
    p=np.asarray(d['event_pitch_semitones'],float);t=np.asarray(d['event_onset_s'],float)
    span=np.asarray(d['event_pitch_span_cents'],float);quality=np.asarray(d['event_phase_fraction'],float)
    good=np.isfinite(p)&np.isfinite(span)&(span<=PARAMETERS['max_pitch_span_cents'])&(quality>=PARAMETERS['min_phase_fraction'])
    ft=np.asarray(d['frame_time_s']);fc=np.asarray(d['frame_spectral_centroid_hz'])
    for i in np.flatnonzero(good):
        inside=(ft>=t[i]+.018)&(ft<=float(d['event_offset_s'][i])-.018)
        if not inside.any() or np.median(fc[inside])/(220*2**(p[i]/12))>PARAMETERS['max_centroid_f0_ratio']:good[i]=False
    ids=np.flatnonzero(good)
    return ids,p[ids],t[ids]

def _paths(cost):
    """Two cheapest monotonic paths per cell; pair tuples deduplicate gap ordering."""
    n,m=cost.shape;dp=[[[] for _ in range(m+1)] for _ in range(n+1)];dp[0][0]=[(0.,())];gap=PARAMETERS['gap_cost']
    for i in range(n+1):
        for j in range(m+1):
            if not i and not j:continue
            candidates=[]
            if i and j:candidates.extend((v+float(cost[i-1,j-1]),p+((i-1,j-1),)) for v,p in dp[i-1][j-1])
            if i:candidates.extend((v+gap,p) for v,p in dp[i-1][j])
            if j:candidates.extend((v+gap,p) for v,p in dp[i][j-1])
            seen=set()
            for value,pairs in sorted(candidates,key=lambda x:(x[0],-len(x[1]),x[1])):
                if pairs not in seen:dp[i][j].append((value,pairs));seen.add(pairs)
                if len(dp[i][j])==PARAMETERS['paths_per_cell']:break
    return [p for _,p in dp[n][m] if len(p)>=2]

def _measure(pairs,ri,rp,rt,qi,qp,qt):
    a,b=np.asarray(pairs,int).T;delta=qp[b]-rp[a];shift=float(np.median(delta));residual=delta-shift
    slopes=[(qt[b[j]]-qt[b[i]])/(rt[a[j]]-rt[a[i]]) for i in range(len(a)) for j in range(i+1,len(a)) if rt[a[j]]-rt[a[i]]>.025]
    scale=float(np.median(slopes)) if slopes else 1.;offset=float(np.median(qt[b]-scale*rt[a]));tr=qt[b]-scale*rt[a]-offset
    pl=np.maximum(np.abs(residual)-.05,0)/2;tl=np.maximum(np.abs(tr)-.005,0)*2
    missing=[int(x) for x in ri if x not in ri[a]];inserted=[int(x) for x in qi if x not in qi[b]]
    cost=float((pl.sum()+tl.sum()+.7*(len(missing)+len(inserted)))/max(len(ri),len(qi)))
    return dict(cost=cost,matched_pairs=[[int(i),int(j)] for i,j in zip(ri[a],qi[b])],missing_reference=missing,inserted_query=inserted,
        global_pitch_shift=shift,timing_scale=scale,timing_offset_s=offset,pitch_residual_semitones=residual.tolist(),
        absolute_pitch_change_semitones=delta.tolist(),onset_change_s=(qt[b]-rt[a]).tolist(),timing_residual_s=tr.tolist(),
        mean_pitch_loss=float(pl.mean()),exact_pitch_fraction=float(np.mean(np.abs(residual)<=.2)),mean_timing_loss=float(tl.mean()))

def evidence(reference,query):
    ri,rp,rt=events(reference);qi,qp,qt=events(query);n,m=len(ri),len(qi)
    if min(n,m)<2:return dict(available=False,features=[1e3,0,0,0,1e3,0,1e3,1,1,1,np.log1p(n),np.log1p(m)],paths=[],reference_events=n,query_events=m)
    diff=qp[None,:]-rp[:,None];values,counts=np.unique(np.round(diff.ravel(),1),return_counts=True)
    candidates=sorted(zip(counts,values),key=lambda x:(-x[0],abs(x[1]),x[1]))[:PARAMETERS['shift_proposals']]
    shifts=sorted(set([0.]+[float(x[1]) for x in candidates]));proposals=set()
    rnorm=(rt-rt[0])/max(rt[-1]-rt[0],.01);qnorm=(qt-qt[0])/max(qt[-1]-qt[0],.01)
    for shift in shifts:
        c=np.maximum(np.abs(diff-shift)-.05,0)/2+.15*np.abs(rnorm[:,None]-qnorm[None,:])
        proposals.update(_paths(c))
    if not proposals:return dict(available=False,features=[1e3,0,0,0,1e3,0,1e3,1,1,1,np.log1p(n),np.log1p(m)],paths=[],reference_events=n,query_events=m)
    measured=[_measure(p,ri,rp,rt,qi,qp,qt) for p in proposals]
    measured.sort(key=lambda p:(p['cost'],-len(p['matched_pairs']),abs(p['global_pitch_shift']),p['matched_pairs']))
    best=measured[0];k=len(best['matched_pairs']);paths=[p for p in measured if p['cost']<=best['cost']+.15][:4]
    features=[best['cost'],np.log1p(k),k/n,k/m,best['mean_pitch_loss'],best['exact_pitch_fraction'],best['mean_timing_loss'],
        len(best['missing_reference'])/n,len(best['inserted_query'])/m,1-m/max(1,len(query['event_onset_s'])),np.log1p(n),np.log1p(m)]
    return dict(available=True,features=list(map(float,features)),paths=paths,reference_events=n,query_events=m)

def score(e,config):
    if not e['available']:return -1e6
    x=(np.asarray(e['features'])-config['mean'])/config['scale']
    return float(np.dot(x,config['coef'])+config['intercept'])

def simple_scores(reference,query):
    count=-abs(len(reference['event_onset_s'])-len(query['event_onset_s']))
    r=equal_bins(np.asarray(reference['frame_rms']),64).astype(float);q=equal_bins(np.asarray(query['frame_rms']),64).astype(float)
    r=r/max(float(np.linalg.norm(r)),1e-12);q=q/max(float(np.linalg.norm(q)),1e-12)
    return dict(count=float(count),envelope=-float(np.linalg.norm(r-q)))

def explain(reference,query,e):
    """Every missing correspondence retains its acoustic evidence and uncertainty."""
    out=[];ft=np.asarray(query['frame_time_s']);energy=np.asarray(query['frame_rms']);floor=max(1e-5,float(energy.max())*.01)
    _,_,_=events(query)
    for p in e['paths']:
        missing=[]
        for index in p['missing_reference']:
            onset=float(reference['event_onset_s'][index])*p['timing_scale']+p['timing_offset_s']
            offset=float(reference['event_offset_s'][index])*p['timing_scale']+p['timing_offset_s']
            inside=(ft>=onset+.020)&(ft<=offset-.020)
            maximum=float(energy[inside].max()) if inside.any() else None
            quiet=maximum is not None and maximum<=floor
            missing.append(dict(reference_event=index,expected_interval_s=[onset,offset],measured_max_rms=maximum,quiet_threshold_rms=floor,
                status='quiet_at_predicted_location' if quiet else 'unresolved_observation',
                supported_accounts=['no_audible_counterpart'] if quiet else ['weak_or_masked_event','merged_or_displaced_event','absent_event_with_other_sound'],
                physical_cause='not_identified'))
        pitch=[dict(reference_event=pair[0],query_event=pair[1],semitones=v,kind='detuning' if abs(v)<1.5 else 'substitution') for pair,v in zip(p['matched_pairs'],p['pitch_residual_semitones']) if abs(v)>.2]
        timing=[dict(reference_event=pair[0],query_event=pair[1],seconds=v) for pair,v in zip(p['matched_pairs'],p['timing_residual_s']) if abs(v)>.015]
        out.append(dict(**p,missing_evidence=missing,pitch_edits=pitch,timing_edits=timing,
            observation_statement='Original acoustic measurements retained; correspondences and expected locations are separate hypotheses.'))
    return out

def decide(memory,query,config):
    """Memory is a sequence of (opaque handle, acoustic description). No truth keys."""
    candidates=[]
    for handle,d in memory:
        ev=evidence(d,query);value=score(ev,config)
        if value>=config['threshold']:candidates.append(dict(handle=handle,support_logit=value,accounts=explain(d,query,ev)))
    return dict(status='unsupported_memory' if not candidates else 'one_supported_memory' if len(candidates)==1 else 'ambiguous_memories',candidates=candidates)
