"""Separate process: only arrived waveform bytes and fixed model parameters enter."""
import sys, json, base64, os, hashlib
import numpy as np
from model import observe, forecast, CAPACITY

# Complete numerical imports/initialization before the filesystem/API guard.
observe(np.zeros(1920,dtype='<f4').tobytes())
blocked=[]
def guard(event,args):
    if event=='open' or event in ('os.listdir','os.scandir','os.chdir','os.system','subprocess.Popen') or event.startswith(('socket.','ctypes.')):
        blocked.append(event)
        raise PermissionError('Predictor process filesystem/network/process access denied')
sys.addaudithook(guard)
try:
    open('FORBIDDEN_PROBE','rb')
except PermissionError:
    pass
else:
    raise AssertionError('Filesystem guard inactive')

history=[]; prefix=[]; config=None; arrivals=0; evictions=0; resets=0
for line in sys.stdin:
    msg=json.loads(line);kind=msg.pop('op')
    if kind=='init':
        assert set(msg)=={'config'}
        config=msg['config'];history=[];prefix=[];arrivals=evictions=resets=0
        result={'ready':True,'guard_probe_blocked':blocked==['open'],'capacity':CAPACITY}
    elif kind=='arrive':
        assert set(msg)=={'samples_b64'}
        raw=base64.b64decode(msg['samples_b64']); assert len(raw)<=2*16000*4
        obs=observe(raw,config['adapter']);history.append(obs);prefix.append(obs['wave_sha256']);arrivals+=1
        if len(history)>CAPACITY:history.pop(0);evictions+=1
        result={'observation':obs,'occupancy':len(history),'evictions':evictions,'arrivals':arrivals}
    elif kind=='reset':
        assert not msg;history=[];resets+=1
        result={'occupancy':0,'deliberate_resets':resets,'evictions':evictions}
    elif kind=='forecast':
        assert not msg
        result={'forecasts':forecast(history,config),'prefix_sha256':hashlib.sha256(json.dumps(prefix,separators=(',',':')).encode()).hexdigest(),
                'memory_sha256':hashlib.sha256(json.dumps(history,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'occupancy':len(history),'evictions':evictions,'arrivals':arrivals,'deliberate_resets':resets,
                'guard_blocked_events':list(blocked)}
    else:
        raise ValueError('Only init, arrive, reset and forecast are accepted')
    print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False),flush=True)
