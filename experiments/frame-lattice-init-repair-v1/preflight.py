"""One disposable fixed-smoke test; same worker prefix and unchanged guard."""
import json,time,hashlib,pickle,base64,traceback
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
cfg=json.loads((P/'initial_model.json').read_text());worker=(P/'worker.py').read_text();prefix=worker.split('listener=None')[0];hashes={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['model.py','worker.py','preflight.py','initial_model.json']}
# Fixed synthetic initialization buffer, unrelated to scientific split/generator.
parts=[np.zeros(1024,dtype='<f4')]
for pitch in [0,-3,-7,-3,0,-5,-7,3,0,-3,-7]:
 t=np.arange(1536)/16000;parts.append((.1*np.sin(2*np.pi*220*2**(pitch/12)*t)).astype('<f4'))
parts.append(np.zeros(2048,dtype='<f4'));raw=np.concatenate(parts).tobytes();raw+=bytes((-len(raw))%4096);start=time.time_ns();ns={};operations=[];result={'all_pass':False,'source_hashes':hashes,'initialization':'np.median float arrays odd/even before unchanged audit hook','smoke_sha256':hashlib.sha256(raw).hexdigest(),'smoke_samples':len(raw)//4,'start_utc_ns':start}
try:
 exec(compile(prefix,'worker-prefix','exec'),ns)
 listener=ns['Listener'](cfg);operations.append('init')
 for i in range(0,len(raw),4096):listener.arrive(raw[i:i+4096]);operations.append('arrive')
 before=json.dumps(listener.forecast(),sort_keys=True,separators=(',',':'),allow_nan=False);operations.append('forecast');state=pickle.dumps(listener,protocol=4);operations.append('save');listener=pickle.loads(state);operations.append('restore');after=json.dumps(listener.forecast(),sort_keys=True,separators=(',',':'),allow_nan=False);operations.append('forecast_after_restore');assert before==after
 listener.reset();operations.append('reset');listener.forecast();operations.append('forecast_after_reset')
 try:open('FORBIDDEN_AFTER_SMOKE','rb')
 except PermissionError:operations.append('forbidden_open_blocked')
 else:raise AssertionError('Guard did not block deliberate open')
 assert ns['blocked']==['open','open'];result.update(all_pass=True,same_forecast_bytes=True,forecast_sha256=hashlib.sha256(before.encode()).hexdigest(),state_sha256=hashlib.sha256(state).hexdigest())
except BaseException as e:
 tb=e.__traceback__;trace=[]
 while tb is not None:
  trace.append({'file':Path(tb.tb_frame.f_code.co_filename).name,'line':tb.tb_lineno,'function':tb.tb_frame.f_code.co_name});tb=tb.tb_next
 result.update(error_type=type(e).__name__,error=str(e),trace=trace)
result.update(operations=operations,guard_events=ns.get('blocked',[]),end_utc_ns=time.time_ns());print(json.dumps(result,sort_keys=True,allow_nan=False),flush=True)
