from __future__ import annotations
import json,re
from pathlib import Path
SECRET_PATTERNS=[re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*[\"']?[^\s\"']{8,}")]
def inspect_notebook(path:str|Path)->dict:
    p=Path(path); obj=json.loads(p.read_text(encoding='utf-8'))
    cells=obj.get('cells',[]); code=[c for c in cells if c.get('cell_type')=='code']; md=[c for c in cells if c.get('cell_type')=='markdown']
    src='\n'.join(''.join(c.get('source',[])) for c in code); execs=[c.get('execution_count') for c in code if c.get('execution_count') is not None]
    return {'path':str(p),'cells':len(cells),'code_cells':len(code),'markdown_cells':len(md),'executed_cells':len(execs),'execution_monotonic':execs==sorted(execs) if execs else True,'embedded_outputs':sum(len(c.get('outputs',[])) for c in code),'possible_secrets':sum(bool(pat.search(src)) for pat in SECRET_PATTERNS)}
