from __future__ import annotations
import json
from pathlib import Path
from .._resources import resource_root
class DomainPackRegistry:
    def __init__(self,root=None):
        self.root=Path(root) if root else resource_root()/'profiles'/'domain_packs'
    def names(self):return sorted(p.stem for p in self.root.glob('*.json'))
    def load(self,name):return json.loads((self.root/f'{name}.json').read_text(encoding='utf-8'))
    def route(self,text:str):
        low=text.lower();hits=[]
        for n in self.names():
            p=self.load(n);score=sum(t.lower() in low for t in p.get('triggers',[]))
            if score:hits.append({'name':n,'score':score,'profile':p})
        return sorted(hits,key=lambda x:x['score'],reverse=True)
