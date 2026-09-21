"""Lossless gzip record shards; bounded Git file size, no changes to record bytes."""
import gzip
from pathlib import Path
class Writer:
 def __init__(self,path,mode):self.path=Path(path);self.mode=mode;self.index=0;self.f=gzip.open(self.path,mode,encoding='utf-8',compresslevel=6)
 def write(self,s):
  if self.f.buffer.fileobj.tell()>=64*1024**2:
   self.f.close();self.index+=1;self.f=gzip.open(str(self.path)+f'.part{self.index:03}.gz',self.mode,encoding='utf-8',compresslevel=6)
  return self.f.write(s)
 def flush(self):return self.f.flush()
 def fileno(self):return self.f.fileno()
 def close(self):return self.f.close()
def open_record(path,mode):return Writer(path,mode)
def read_lines(path):
 p=Path(path);out=[]
 for f in [p]+sorted(p.parent.glob(p.name+'.part*.gz')):
  with gzip.open(f,'rt') as stream:out.extend(stream.read().splitlines())
 return out
