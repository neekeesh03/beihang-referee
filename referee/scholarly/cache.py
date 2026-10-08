import json,time,hashlib
from pathlib import Path
class JsonSearchCache:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def _p(self,provider,query):return self.root/(hashlib.sha256(f'{provider}|{query}'.encode()).hexdigest()+'.json')
    def get(self,provider,query,max_age_s=86400):
        p=self._p(provider,query)
        if not p.exists() or time.time()-p.stat().st_mtime>max_age_s:return None
        return json.loads(p.read_text())
    def put(self,provider,query,data):self._p(provider,query).write_text(json.dumps(data,ensure_ascii=False,indent=2))
