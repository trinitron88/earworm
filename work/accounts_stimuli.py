"""Experiment08: mixed edits and observation failures, with withheld truth."""
import sys,json,hashlib,argparse
from pathlib import Path
sys.dont_write_bytecode=True
import numpy as np
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parent;SR=24000;SECONDS=2.;SIZE=48000;SEED=2026091908
STEP=.165;DURATION=.100;LEAD=.13
CORE=('exact','transpose','detune','timing','delete_rest','delete_closed','delete_two','substitute','insert','delete_insert','weak_present','mask_present','mask_absent','merged','legitimate_rest')
STACKS=('delete_transpose','delete_timing','delete_detune')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def render(notes,root,amps,phases,gain,noise=None):
 audio=np.zeros(SIZE,float)
 for e in notes:
  if not e['present']:continue
  start=round(e['onset']*SR);count=round(e['duration']*SR);t=np.arange(count)/SR
  hz=root*2**(e['pitch']/12);h=np.arange(1,len(amps)+1)
  wave=np.sum(amps[:,None]*np.sin(2*np.pi*hz*h[:,None]*t[None,:]+phases[e['phase_key'],:,None]),axis=0)
  attack=min(round(.018*SR),count//3);release=min(round(.025*SR),count//3);env=np.ones(count)
  env[:attack]=np.sin(np.linspace(0,np.pi/2,attack))**2;env[-release:]=np.cos(np.linspace(0,np.pi/2,release))**2
  assert start>=0 and start+count<=SIZE
  audio[start:start+count]+=wave*env*gain*e['amplitude']
 if noise is not None:audio+=noise
 return audio.astype(np.float32)
def base_notes(pitches):return [{'ref_position':i,'pitch':float(p),'phase_key':int(p),'onset':LEAD+i*STEP,'duration':DURATION,'amplitude':1.,'present':True} for i,p in enumerate(pitches)]
def generate(outdir=None,saved=None):
 out=Path(outdir) if outdir else ROOT/'accounts_stimuli';out.mkdir(exist_ok=True,parents=True);(out/'blocks').mkdir(exist_ok=True)
 if saved:
  prior=json.loads(Path(saved).read_text());excluded={tuple(p) for p in prior['excluded_patterns']};provenance=prior['prior_provenance']
 else:
  p=ROOT/'confidence_stimuli/manifest.json';old=json.loads(p.read_text());excluded={tuple(v) for v in old['excluded_prior_interval_patterns']}|{tuple(v) for g in old['groups'] for v in g['base_interval_patterns']};provenance={'path':'confidence_stimuli/manifest.json','sha256':sha(p)}
 assert len(excluded)==1032
 used=set(excluded);rng=np.random.default_rng(SEED);blocks=[];groups=[];ambiguity=[]
 def fresh(length,palette=None):
  for _ in range(10000):
   p=list(map(int,rng.choice(np.arange(19) if palette is None else palette,length,replace=False)));pattern=tuple(np.diff(p))
   if pattern not in used:used.add(pattern);return p
  raise RuntimeError('Fresh pattern sampling exhausted')
 for gi in range(24):
  gid=f'e{gi:02d}';n=(4,6,8,10)[gi%4];split='fit' if gi<4 else 'calibration' if gi<8 else 'held_out'
  palette=sorted(map(int,rng.choice(19,n,replace=False)));a=fresh(n,palette);b=fresh(n,palette);orders=[a,b]
  for original in (a,b):
   for _ in range(1000):
    p=original.copy();i,j=rng.choice(n,2,replace=False);p[i],p[j]=p[j],p[i];pattern=tuple(np.diff(p))
    if pattern not in used:used.add(pattern);orders.append(p);break
   else:raise RuntimeError('No fresh hard foil')
  orders += [fresh(n,palette) for _ in range(4)]+[fresh(n-1),fresh(n+1 if n<10 else 9)]
  mid=n//2;other=(mid+1)%n
  for pitch in rng.permutation(19):
   twin=a.copy();twin[mid]=int(pitch);pat=tuple(np.diff(twin))
   if pitch!=a[mid] and pat not in used:used.add(pat);break
  orders.append(twin)
  root=float(rng.uniform(195,245));amps=np.arange(1,9,dtype=float)**(-float(rng.uniform(1.3,1.8)));phases=rng.uniform(-np.pi,np.pi,(19,8))
  raw=render(base_notes(a),root,amps,phases,1.);gain=.085/float(np.sqrt(np.mean(raw.astype(float)**2)))
  ids={}
  def add(suffix,notes,role,family='base',source=None,noise=None):
   bid=f'{gid}_{suffix}';pcm=render(notes,root,amps,phases,gain,noise);assert np.max(np.abs(pcm))<.98
   path=out/'blocks'/f'{bid}.wav';wavfile.write(path,SR,pcm)
   blocks.append({'id':bid,'group_id':gid,'split':split,'role':role,'family':family,'source':source,'reference_id':f'{gid}_reference_{source}' if source else None,'audio_path':str(path.resolve()),'audio_sha256':hashlib.sha256(pcm.tobytes()).hexdigest(),'notes':notes,'reference_length':n,'target_position':mid,'other_position':other,'phase':'stack' if family in STACKS else 'core','duration_s':SECONDS})
   ids[suffix]=bid;return pcm
  for k,(label,order) in enumerate(zip(['reference_a','reference_b']+[f'distractor_{i}' for i in range(8)]+['twin_a'],orders)):
   add(label,base_notes(order),'reference' if k<2 else 'distractor' if k<10 else 'twin',source=('a','b')[k] if k<2 else None)
  for source,order in zip(('a','b'),(a,b)):
   noise=np.zeros(SIZE);lo=round((LEAD+mid*STEP-.010)*SR);hi=round((LEAD+mid*STEP+DURATION+.010)*SR)
   nr=rng.normal(size=hi-lo);noise[lo:hi]=nr*.14;noise=np.convolve(noise,np.array([.25,.5,.25]),mode='same').astype(np.float32)
   for family in CORE+STACKS:
    notes=base_notes(order);extra_noise=None
    if family in ('delete_rest','delete_closed','delete_two','delete_insert')+STACKS:notes[mid]['present']=False
    if family=='delete_two':notes[n-1]['present']=False
    if family=='delete_closed':
     for e in notes[mid+1:]:e['onset']-=STEP
    if family in ('transpose','delete_transpose'):
     for e in notes:e['pitch']+=3
    if family in ('detune','delete_detune'):notes[other]['pitch']+=.5
    if family=='substitute':notes[mid]['pitch']+=3
    if family in ('timing','delete_timing'):notes[other]['onset']+=.045
    if family=='legitimate_rest':
     for e in notes[mid:]:e['onset']+=.080
    if family=='weak_present':notes[mid]['amplitude']=.035
    if family in ('mask_present','mask_absent'):
     notes[mid]['amplitude']=.10;notes[mid]['present']=family=='mask_present';extra_noise=noise
    if family=='merged':notes[mid]['onset']=notes[mid-1]['onset']+DURATION-.004
    if family in ('insert','delete_insert'):
     pitch=int(rng.choice([x for x in range(19) if x not in order]));notes.append({'ref_position':None,'pitch':float(pitch),'phase_key':pitch,'onset':LEAD+n*STEP,'duration':DURATION,'amplitude':1.,'present':True})
    add(f'query_{source}_{family}',notes,'query',family,source,extra_noise)
  group={'id':gid,'split':split,'length':n,'reference_a_id':ids['reference_a'],'reference_b_id':ids['reference_b'],'distractor_ids':[ids[f'distractor_{i}'] for i in range(8)],'twin_id':ids['twin_a'],'ambiguity_query_id':ids['query_a_delete_rest'],'root_hz':root,'amplitudes':amps.tolist(),'phases':phases.tolist(),'gain':gain,'base_orders':orders,'base_patterns':[list(map(int,np.diff(p))) for p in orders]}
  groups.append(group)
  expected=next(x for x in blocks if x['id']==ids['query_a_delete_rest']);notes=base_notes(twin);notes[mid]['present']=False
  assert hashlib.sha256(render(notes,root,amps,phases,gain).tobytes()).hexdigest()==expected['audio_sha256']
  ambiguity.append({'group_id':gid,'query_id':ids['query_a_delete_rest'],'compatible_references':[ids['reference_a'],ids['twin_a']]})
 manifest={'experiment':8,'seed':SEED,'groups':groups,'blocks':blocks,'ambiguity_cases':ambiguity,'excluded_patterns':sorted(map(list,excluded)),'prior_provenance':provenance,'core_families':list(CORE),'stack_order':list(STACKS),'renderer':'new variable-length additive waveform construction; metadata evaluation-only','model_input_contract':'Only PCM/sample rate; IDs used solely for routing.'}
 patterns=[tuple(v) for g in groups for v in g['base_patterns']];assert len(patterns)==len(set(patterns))==264 and not set(patterns)&excluded
 assert len(blocks)==1128
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'routing.json').write_text(json.dumps([{'id':b['id'],'audio_path':b['audio_path']} for b in blocks],indent=2)+'\n')
 print(json.dumps({'blocks':len(blocks),'groups':len(groups),'base_patterns':len(patterns),'excluded':len(excluded),'lengths':[4,6,8,10],'all_24_ambiguity_waveforms_identical':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir');p.add_argument('--saved');a=p.parse_args();generate(a.outdir,a.saved)
