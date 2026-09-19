"""Reproduce only saved-data audit calculations in a fresh temporary directory."""
import argparse,hashlib,json,platform,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--record',type=Path,required=True);a=ap.parse_args();base=Path(__file__).resolve().parent
    compared=[]
    with tempfile.TemporaryDirectory(prefix='earworm-pair-audit-check-') as tmp:
        out=Path(tmp)/'results'
        subprocess.run([sys.executable,'-B',str(base/'analyze_saved_pairs.py'),'--root',str(a.root),'--out',str(out)],check=True,stdout=subprocess.DEVNULL)
        for p in sorted((base/'results').iterdir()):
            assert p.read_bytes()==(out/p.name).read_bytes(),p.name
            compared.append(dict(file=p.name,byte_identical=True,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    record=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=np.__version__,
                clean_audit_reexecution=compared,checks=json.loads((base/'results/verification.json').read_text()),
                scope='Only saved-data arithmetic was rerun; no original experiment pipeline, audio, alignment search, training, or replay.')
    a.record.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
