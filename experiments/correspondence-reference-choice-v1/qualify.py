"""Finite, durably charged NON-MUSICAL correctness probes. Never runs musical panel."""
import datetime,json,pathlib,sys,time,traceback
import numpy as np
from fixtures import fixture
from engine import predict
from matching import subsequence_dtw
ROOT=pathlib.Path(__file__).resolve().parent

CASES=[
 ('D-ordinary','D','ordinary',1.,0,6.,'identity'),
 ('D-known-uncharged-skip','D-primitive','ordinary',1.,0,6.,'literal_skip'),
 ('G-positive','G','ordinary',1.25,2,6.,'identity'),
 ('exact-positive','G-exact','ordinary',1.25,2,6.,'identity'),
 ('G-negative','G','ordinary',.8,-2,6.,'identity'),
 ('exact-negative','G-exact','ordinary',.8,-2,6.,'identity'),
 ('G-bracket-phase','G','ordinary',1.,0,6.03,'identity'),
 ('exact-bracket-phase','G-exact','ordinary',1.,0,6.03,'identity'),
 ('G-nonuniform','G','nonuniform',1.,0,6.,'reject'),
 ('exact-nonuniform','G-exact','nonuniform',1.,0,6.,'reject'),
 ('G-no-match','G','no_match',1.,0,6.,'reject'),
 ('exact-no-match','G-exact','no_match',1.,0,6.,'reject'),
 ('G-hole','G','hole',1.,0,6.,'reject'),
 ('exact-hole','G-exact','hole',1.,0,6.,'reject'),
 ('G-ties','G','ties',1.,0,10.,'ties'),
 ('exact-ties','G-exact','ties',1.,0,10.,'ties'),
 ('G-constant-uncertainty','G','constant',1.,0,6.,'uncertain'),
 ('G-missing-query','G','missing_query',1.,0,6.,'reject'),
 ('G-silence-contradiction','G','silence',1.,0,6.,'reject'),
 ('G-repeated-pitch','G','repeat',1.,0,6.,'identity'),
 ('G-scale-lower-bound','G','long_source',.65,0,6.,'identity'),
 ('exact-scale-lower-bound','G-exact','long_source',.65,0,6.,'identity'),
 ('exact-out-of-range','G-exact','ordinary',1.6,0,6.,'reject'),
]

def main():
    q=ROOT/'qualification';q.mkdir(exist_ok=True);lp=q/'ledger.json'
    ledger=json.loads(lp.read_text()) if lp.exists() else {'cap':32,'calls':[]}
    requested=sys.argv[1:] or [x[0] for x in CASES]
    known={x[0]:x for x in CASES}
    for name in requested:
        case=known[name]
        if any(c['name']==name and c.get('passed') for c in ledger['calls']):continue
        assert len(ledger['calls'])<32
        name,method,kind,scale,shift,offset,expect=case
        call={'name':name,'method':method,'expectation':expect,'expected_scale':scale,'expected_shift':shift,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':False}
        ledger['calls'].append(call);lp.write_text(json.dumps(ledger,indent=2)+'\n')
        began=time.monotonic()
        try:
            rows,exact=fixture(kind,scale,shift,offset)
            if method=='D-primitive':
                a=np.eye(3);answer=subsequence_dtw(a,a[[0,2]])
                assert answer['cost']==0 and answer['path']==[(0,0),(2,1)]
            else:
                answer=predict(exact if method=='G-exact' else rows,method)
                if expect=='identity':
                    assert answer['accepted'],answer.get('reason')
                    s=answer['selected'];assert 0<=s['center']<(4.2 if kind=='long_source' else 3) and s['shift']==shift,s
                    if method!='D':
                        assert s['scale_range'][0]-1e-9<=scale<=s['scale_range'][1]+1e-9,s['scale_range']
                        assert s['query_rows_skipped']==0
                        if method=='G-exact':assert abs(s['scale']-scale)<1e-8
                elif expect=='reject':assert not answer['accepted'],answer
                elif expect=='ties':assert not answer['accepted'] and len(answer['candidates'])>=2,answer
                elif expect=='uncertain':
                    assert answer['candidates'];assert all(c['parameter_uncertain'] and c['scale_range'][1]-c['scale_range'][0]>.1 for c in answer['candidates'])
            call.update(passed=True,answer=answer)
        except Exception as e:
            call.update(error=type(e).__name__,detail=str(e),traceback=traceback.format_exc())
        call['compute_seconds']=time.monotonic()-began
        lp.write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n')
        print(name,call['passed'],call.get('error',''),flush=True)
        if not call['passed']:break
    ledger['qualified']=all(any(c['name']==x[0] and c.get('passed') for c in ledger['calls']) for x in CASES)
    lp.write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'qualified':ledger['qualified'],'charged_probes':len(ledger['calls'])}))

if __name__=='__main__':main()
