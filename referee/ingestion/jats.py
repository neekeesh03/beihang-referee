from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
def inspect_jats(path:str|Path)->dict:
    p=Path(path); root=ET.parse(p).getroot()
    def all_local(name): return [e for e in root.iter() if e.tag.split('}')[-1]==name]
    title=''.join(''.join(e.itertext()) for e in all_local('article-title')[:1]).strip()
    return {'path':str(p),'title':title,'sections':len(all_local('sec')),'references':len(all_local('ref')),'figures':len(all_local('fig')),'tables':len(all_local('table-wrap')),'supplements':len(all_local('supplementary-material'))}
