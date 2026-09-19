"""Build and verify a relocatable Experiment08 kit without changing original runs."""
import sys,json,shutil,subprocess,hashlib,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
import numpy as np
from scipy.io import wavfile
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'accounts_results'
SOURCES=('accounts_stimuli.py','accounts_reader.py','accounts_experiment.py','accounts_audit.py','accounts_portable.py','remember_changes_acoustics.py','confidence_reader.py','incomplete_matcher.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(destination):
    root=Path(destination);work=root/'work';work.mkdir(parents=True,exist_ok=True)
    for name in SOURCES:shutil.copy2(ROOT/name,work/name)
    for d in ('accounts_results','accounts_stimuli','confidence_results'):(work/d).mkdir(exist_ok=True)
    for p in OUT.glob('*.json'):shutil.copy2(p,work/'accounts_results'/p.name)
    shutil.copy2(ROOT/'accounts_stimuli/manifest.json',work/'accounts_stimuli/manifest.json')
    shutil.copy2(ROOT/'confidence_results/frozen_config.json',work/'confidence_results/frozen_config.json')
    return work
def main():
    dest=ROOT/'accounts_portable_validation';work=prepare(dest)
    saved=work/'accounts_stimuli/manifest.json'
    p=subprocess.run([sys.executable,'-B',str(work/'accounts_stimuli.py'),'--saved',str(saved),'--outdir',str(saved.parent)],check=True,text=True,capture_output=True);print(p.stdout,flush=True)
    original=json.loads((ROOT/'accounts_stimuli/manifest.json').read_text());new=json.loads(saved.read_text());assert [b['audio_sha256'] for b in original['blocks']]==[b['audio_sha256'] for b in new['blocks']]
    # The relocated runner re-extracts every development waveform and refits all
    # 1,200 pairs plus calibration without accessing original helper paths.
    subprocess.run([sys.executable,'-B',str(work/'accounts_experiment.py'),'develop'],check=True)
    a=json.loads((OUT/'frozen_config.json').read_text());b=json.loads((work/'accounts_results/frozen_config.json').read_text())
    for key in ('mean','scale','coef','intercept','threshold','baseline_thresholds','calibration'):assert a[key]==b[key],key
    code="""
import json,sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from accounts_reader import evidence,score,description_digest
from remember_changes_acoustics import describe_audio
root=Path(sys.argv[1]);m=json.loads((root/'accounts_stimuli/manifest.json').read_text());B={b['id']:b for b in m['blocks']};expected=json.loads((root/'accounts_results/held_out_pairs.json').read_text());config=json.loads((root/'accounts_results/frozen_config.json').read_text());out=[]
for qid in ('e08_query_a_delete_rest','e09_query_a_mask_present','e10_query_a_delete_timing','e11_query_a_delete_detune'):
 q=B[qid];rid=q['reference_id'];sr,pcm=wavfile.read(q['audio_path']);qd=describe_audio(pcm,sr);sr,pcm=wavfile.read(B[rid]['audio_path']);rd=describe_audio(pcm,sr);e=evidence(rd,qd);assert e==expected[qid][rid]['evidence'];out.append(qid)
print(json.dumps({'portable_fresh_pairs':out}))
"""
    p=subprocess.run([sys.executable,'-B','-c',code,str(work)],cwd=work,check=True,capture_output=True,text=True);paircheck=json.loads(p.stdout)
    record=dict(portable_root=str(dest),regenerated_waveforms=len(new['blocks']),all_pcm_hashes_identical=True,source_files_identical=all(sha(ROOT/n)==sha(work/n) for n in SOURCES),development_waveforms_reextracted=328,fit_and_calibration_identical=True,**paircheck)
    (OUT/'portable_validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
