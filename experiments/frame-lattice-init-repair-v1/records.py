import gzip

def open_record(path,mode):return gzip.open(path,mode,encoding='utf-8',compresslevel=6)
def read_lines(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:return f.read().splitlines()
