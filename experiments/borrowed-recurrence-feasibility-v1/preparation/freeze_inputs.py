"""Create construction/timing manifests without opening evaluation score content."""
import hashlib,json,math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from materials import split_manifest
manifest=split_manifest();labels=[]
for g in manifest['groups']:
 for cell in manifest['cells']:
  a=g['source_onset_seconds'];b=a+3;qa=b+32;stretch=g['stretch_ratio'] if cell=='stretch' else 1.;qb=qa+3*stretch
  labels.append({'group':g['group'],'split':g['split'],'stratum':g['stratum'],'cell':cell,'source_onset':a,'source_offset':b,'query_onset':qa,'query_offset':qb,'decision_time':math.ceil(qb+.25),'shift':(None if cell=='foil' else g['transpose_semitones'] if cell=='transpose' else 0),'stretch':None if cell=='foil' else stretch,'equivalent_occurrences':[{'id':'source','onset':a,'offset':b}],'construction_positive':cell!='foil'})
(ROOT/'labels-and-schedule.json').write_text(json.dumps(labels,indent=2)+'\n')
(ROOT/'input_manifest.json').write_text(json.dumps({'groups':manifest['groups'],'source_manifest_sha256':hashlib.sha256((ROOT/'sources/manifest.json').read_bytes()).hexdigest(),'generation_code_sha256':hashlib.sha256((ROOT/'materials.py').read_bytes()).hexdigest(),'input_status':'Exact source bytes and deterministic construction fixed; evaluation MIDI note content, PCM and derived measurements unexposed and not generated. PCM/archive hashes are recorded after one authorized generation.','labels_and_schedule_sha256':hashlib.sha256((ROOT/'labels-and-schedule.json').read_bytes()).hexdigest()},indent=2)+'\n')
