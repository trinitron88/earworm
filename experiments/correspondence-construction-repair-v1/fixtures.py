"""Deterministic non-musical qualification arrays and separately frozen diagnostics."""
import hashlib,json,math,pathlib
import numpy as np

def rows_for(events,length):
    t=np.arange(int(length)*10,dtype=float)*.1+.05;clean=np.zeros((len(t),129));clean[:,128]=1
    for a,b,p in events:
        ix=(t>=a)&(t<b);clean[ix]=0;clean[ix,int(p)]=1
    return {'t':t,'unit':np.floor(t).astype(np.int32),'rms':1-clean[:,128],'clean':clean,'available_at':np.floor(t).astype(np.int32)+1}

def intervals(pitches,start=0,durations=None):
    durations=np.asarray(durations if durations is not None else [.5]*len(pitches),float)
    ends=start+np.cumsum(durations)
    return np.column_stack([np.r_[start,ends[:-1]],ends,pitches])

def fixture(kind='ordinary',scale=1,shift=0,offset=6):
    source=intervals([10,22,34,46,58,70],durations=[.7]*6 if kind=='long_source' else None);query=source.copy();query[:,:2]=query[:,:2]*scale+offset;query[:,2]+=shift
    history=[source,np.array([[source[-1,1],offset,110.]])]
    if kind=='no_match':query[:,2]+=20
    if kind=='nonuniform':
        query=intervals([10,22,34,46,58,70],offset,[.2,.2,.2,.2,.2,2.])
    if kind=='ties':
        offset=10;query=source+np.array([10.,10.,0.]);history=[source,np.array([[3.,4.,110.]]),source+np.array([4.,4.,0.]),np.array([[7.,10.,110.]])]
    if kind=='constant':
        source=intervals([20],0,[3]);query=intervals([20],6,[3]);history=[source,np.array([[3.,6.,110.]])]
    if kind=='repeat':
        source=intervals([10,22,34,46,58,58]);query=source+np.array([6.,6.,0]);history=[source,np.array([[3.,6.,110.]])]
    if kind=='silence':
        query=np.concatenate([query[:4],np.array([[8.,8.2,58.],[8.4,8.5,58.]]),query[5:]])
    events=np.concatenate(history+[query]);length=math.ceil(float(events[-1,1])+.25);rows=rows_for(events,length)
    if kind=='missing_query':
        keep=np.arange(len(rows['t']))!=int(np.searchsorted(rows['t'],8.05));rows={k:v[keep] for k,v in rows.items()}
    if kind=='hole':
        keep=rows['unit']!=1;rows={k:v[keep] for k,v in rows.items()};events=np.concatenate([np.array([[a,min(b,1.),p] for a,b,p in events if a<1 and min(b,1)>a]).reshape(-1,3),np.array([[max(a,2.),b,p] for a,b,p in events if b>2 and b>max(a,2.)]).reshape(-1,3)])
    units=sorted(set(rows['unit'].tolist()));segments=[]
    for u in units:
        if segments and segments[-1][1]==u:segments[-1][1]=u+1
        else:segments.append([u,u+1])
    exact={**rows,'events':events,'segments':np.array(segments,float),'event_left_clipped':np.zeros(len(events),bool),'event_right_clipped':np.zeros(len(events),bool)}
    return rows,exact

def input_hash(rows):
    h=hashlib.sha256()
    for key in sorted(rows):
        a=np.ascontiguousarray(rows[key]);h.update(key.encode());h.update(a.dtype.str.encode());h.update(json.dumps(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()

def build_diagnostics(output):
    output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True);sessions=[]
    configs=[('skip-middle',0),('skip-late',1),('skip-silence',2),('skip-double',3),('collision-world-a',4),('collision-world-b',5),('collision-transposed',6),('collision-constant',7)]
    for name,i in configs:
        if i<4:
            rows,ex=fixture();r=rows['clean'].copy();indices=[75+i] if i<3 else [75,85]
            for ix in indices:r[ix]=0;r[ix,128 if i==2 else 91]=1
            # Exact event intervals deliberately follow these observed cell labels.
            labels=np.argmax(r,axis=1);events=[];start=0
            for j in range(1,len(labels)+1):
                if j==len(labels) or labels[j]!=labels[start]:
                    if labels[start]!=128:events.append([start*.1,j*.1,int(labels[start])])
                    start=j
            rows['clean']=r;rows['rms']=1-r[:,128];exevents=np.array(events,float);source=[0.,3.];positive=False
        elif i<7:
            rows,ex=fixture('ties');exevents=ex['events'];source=[0.,3.] if i!=5 else [4.,7.];positive=True
            if i==6:
                # Two admissible occurrences with different pitch transformations.
                ix=(rows['t']>=4)&(rows['t']<7);p=np.argmax(rows['clean'][ix],axis=1)+2;rows['clean'][ix]=np.eye(129)[p]
                ix2=(exevents[:,0]>=4)&(exevents[:,1]<=7);exevents=exevents.copy();exevents[ix2,2]+=2
        else:
            rows,ex=fixture('constant');exevents=ex['events'];source=[0.,3.];positive=True
        d=output/name;d.mkdir(exist_ok=True);np.savez_compressed(d/'rows.npz',**rows);np.savez_compressed(d/'exact-events.npz',events=exevents,available_at=np.ceil(exevents[:,1]).astype(int))
        labels={'source_interval':source,'positive':positive,'expected_shift':0,'expected_scale':1.,'family':name,'cell':name,'diagnostic_only':True,'observation_hash':input_hash(rows)}
        (d/'evaluatorlabels.json').write_text(json.dumps(labels,indent=2)+'\n');sessions.append({'id':name})
    (output/'manifest.json').write_text(json.dumps({'sessions':sessions,'separate_from_rate_panel':True},indent=2)+'\n')
    a=output/'collision-world-a';b=output/'collision-world-b'
    with np.load(a/'rows.npz') as z:ha=input_hash({k:z[k] for k in z.files})
    with np.load(b/'rows.npz') as z:hb=input_hash({k:z[k] for k in z.files})
    assert ha==hb
    certificate={'type':'constructed_duplicate-occurrence_provenance_collision','worlds':['collision-world-a','collision-world-b'],'entire_permitted_input_hashes':[ha,hb],
        'incompatible_labels':[[0,3],[4,7]],'query_occurrence':[10,13],
        'explicit_correspondences':[{'history_interval':[0,3],'query_interval':[10,13],'scale':1,'offset':10,'shift':0},{'history_interval':[4,7],'query_interval':[10,13],'scale':1,'offset':6,'shift':0}],
        'independent_check':'Compare every array and dtype in both rows.npz archives, including all history, occupancy, unit, timestamp and availability rows. Both complete source event sequences also match the return under the listed maps.',
        'meaning':'Which identical earlier whole occurrence causally supplied the return is stipulated by the two evaluator worlds and is absent from their identical observations. Abstention or a set of compatible occurrences is required for this contract.',
        'scope':'Deliberate diagnostic construction only. This is not evidence that any musical-panel failure is caused by an information ambiguity.'}
    (output/'ambiguity-certificate.json').write_text(json.dumps(certificate,indent=2)+'\n')
