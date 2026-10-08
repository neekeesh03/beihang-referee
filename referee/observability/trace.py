import json,time
from pathlib import Path
class TraceRecorder:
    def __init__(self,path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
    def record(self,name,**data):
        with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':time.time(),'name':name,'data':data},default=str)+'\n')
