"""Independent saved-alignment checks and scalar forecast reconstruction."""
import math,statistics
import numpy as np

def enumerate_matches(frames,cfg,name):
    active=[i for i,z in enumerate(frames) if z['observation']['rms']>=.01]
    if not active:return []
    end=active[-1];n=1 if name=='single' else 24;start=end-n+1
    if start<0:return []
    q=frames[start:end+1]
    if not any(z['observation']['pitch_semitones'] is not None for z in q):return []
    allc=[]
    for length in ([1] if name=='single' else [19,24,29]):
        for lo in range(max(0,start-length-7+1)):
            hi=lo+length-1;indices=np.rint(np.linspace(lo,hi,n)).astype(int).tolist();pairs=list(zip(q,[frames[i] for i in indices]));diff=[a['observation']['pitch_semitones']-b['observation']['pitch_semitones'] for a,b in pairs if a['observation']['pitch_semitones'] is not None and b['observation']['pitch_semitones'] is not None];coverage=len(diff)/n
            if coverage<.75:continue
            shift=0. if name=='absolute' else statistics.median(diff);res=sum(abs(v-shift) for v in diff)/len(diff);spectral=sum(sum(abs(x-y) for x,y in zip(a['spectral_shape'],b['spectral_shape']))/2 for a,b in pairs)/n;energy=sum(abs(math.log(max(a['observation']['rms'],1e-8)/max(b['observation']['rms'],1e-8))) for a,b in pairs)/n;cost=res+2*(1-coverage)+.05*spectral+.02*energy
            if cost>.6:continue
            if not any(frames[hi+j]['observation']['pitch_semitones'] is not None for j in [4,5,6,7]):continue
            allc.append((cost,lo,hi))
    allc.sort();selected=[]
    for c in allc:
        if all(c[2]<x[1] or c[1]>x[2] for x in selected):selected.append(c)
        if len(selected)==2:break
    return selected

def verify_readout(frames,cfg,name,f):
    cs=f['lookup_evidence'];anchor=f['anchor_semitones'];expected=enumerate_matches(frames,cfg,name)
    assert len(cs)==len(expected)
    for a,b in zip(cs,expected):assert abs(a['cost']-b[0])<1e-12 and (a['source_first_frame'],a['source_last_frame'])==(b[1],b[2])
    if not cs:
        assert f['point_pitch_semitones'] is None and f['probabilities'][-1]==1
        return f['probabilities'],None
    assert 1<=len(cs)<=2
    for c in cs:
        qs=c['query_first_frame'];qe=c['query_last_frame'];lo=c['source_first_frame'];hi=c['source_last_frame'];n=qe-qs+1;assert n==(1 if name=='single' else 24);assert hi+7<qs
        assert hi-lo+1 in ([1] if name=='single' else [19,24,29]);assert c['aligned_frame_indices']==sorted(c['aligned_frame_indices']) and c['aligned_frame_indices'][0]==lo and c['aligned_frame_indices'][-1]==hi
        pairs=[(frames[a],frames[b]) for a,b in zip(range(qs,qe+1),c['aligned_frame_indices'])];diff=[a['observation']['pitch_semitones']-b['observation']['pitch_semitones'] for a,b in pairs if a['observation']['pitch_semitones'] is not None and b['observation']['pitch_semitones'] is not None];shift=0. if name=='absolute' else statistics.median(diff);coverage=len(diff)/n;res=sum(abs(v-shift) for v in diff)/len(diff);spectral=sum(sum(abs(x-y) for x,y in zip(a['spectral_shape'],b['spectral_shape']))/2 for a,b in pairs)/n;energy=sum(abs(math.log(max(a['observation']['rms'],1e-8)/max(b['observation']['rms'],1e-8))) for a,b in pairs)/n;cost=res+2*(1-coverage)+.05*spectral+.02*energy
        for key,value in [('cost',cost),('pitch_shift',shift),('coverage',coverage),('pitch_residual',res),('spectral_difference',spectral),('energy_log_ratio_abs',energy)]:assert abs(c[key]-value)<1e-12
        assert coverage>=.75 and cost<=.6+1e-12
        future=[frames[hi+j]['observation']['pitch_semitones'] for j in [4,5,6,7]];future=[v for v in future if v is not None];assert abs(c['prediction_pitch']-(statistics.median(future)+shift))<1e-12
        assert c['source_start_sample']==frames[lo]['start_sample'] and c['source_end_sample']==frames[hi]['end_sample']
    assert all(cs[i]['source_last_frame']<cs[j]['source_first_frame'] or cs[i]['source_first_frame']>cs[j]['source_last_frame'] for i in range(len(cs)) for j in range(i))
    p=[0.]*50;weights=[math.exp(-c['cost']/.1) for c in cs];sw=sum(weights)
    for c,w in zip(cs,weights):
        delta=c['prediction_pitch']-anchor;m=[math.exp(-.5*((j-delta)/.08)**2) for j in range(-24,25)];sm=sum(m)
        if sm==0:p[-1]+=w/sw
        else:
            for j,v in enumerate(m):p[j]+=w/sw*v/sm
    p=[.999*v+.001/50 for v in p];j=max(range(50),key=p.__getitem__);return p,None if j==49 else anchor+j-24

def recognition(f,t):
    cs=f['lookup_evidence'];best=cs[0] if cs else None;regions=t['source_regions'];correct=False;transform=False;alignment_error=None
    if best:
        for r in regions:
            overlap=max(0,min(r['end'],best['source_end_sample'])-max(r['start'],best['source_start_sample']));fraction=overlap/max(1,best['source_end_sample']-best['source_start_sample']);end_error=abs(best['source_end_sample']-r['end'])/16000
            if fraction>=.8 and end_error<=.064:
                correct=True;alignment_error=end_error;transform=abs(best['pitch_shift']-r['pitch_shift'])<=.35 and abs(best['time_ratio']-r['time_ratio'])<=.20
    return {'source_accuracy':float(correct),'false_match':float(best is not None) if t['unrelated'] else 0.,'rejection':float(best is None),'transformation_accuracy':float(correct and transform),'alignment_coverage':best['coverage'] if best else 0.,'alignment_end_error':alignment_error}
