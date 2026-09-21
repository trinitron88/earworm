import sys,json,base64,pickle,numpy as np
from model import Listener,accepted
accepted.periodicity(np.zeros(512,dtype='<f4').tobytes(),{'periodicity_threshold':.85,'threshold_grid':[.85,.9,.95],'min_hz':80,'max_hz':2000,'rms_floor':.01})
# Initialize the exact numerical helper before the unchanged audit hook.
np.median(np.array([0.,1.,2.]))
np.median(np.array([0.,1.]))
blocked=[]
def guard(event,args):
    if event=='open' or event in ('os.listdir','os.scandir','os.chdir','os.system','subprocess.Popen') or event.startswith(('socket.','ctypes.')):
        blocked.append(event);raise PermissionError('No filesystem/network/process access')
sys.addaudithook(guard)
try:open('FORBIDDEN','rb')
except PermissionError:pass
else:raise AssertionError('Guard missing')
listener=None
for line in sys.stdin:
    m=json.loads(line);op=m.pop('op')
    if op=='init':
        assert set(m)=={'config'};listener=Listener(m['config']);out={'ready':True,'guard_probe_blocked':blocked==['open']}
    elif op=='arrive':
        assert set(m)=={'samples_b64'};out=listener.arrive(base64.b64decode(m['samples_b64']))
    elif op=='reset':
        assert not m;listener.reset();out={'reset_at_sample':listener.total}
    elif op=='save':
        assert not m;out={'state_b64':base64.b64encode(pickle.dumps(listener,protocol=4)).decode()}
    elif op=='restore':
        assert set(m)=={'state_b64'};listener=pickle.loads(base64.b64decode(m['state_b64']));out={'restored':True}
    elif op=='forecast':
        assert not m;out=listener.forecast();out['guard_blocked_events']=blocked.copy()
    else:raise ValueError('Only init/arrive/reset/forecast')
    print(json.dumps(out,sort_keys=True,separators=(',',':'),allow_nan=False),flush=True)
