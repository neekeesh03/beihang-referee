from __future__ import annotations
import json
from pathlib import Path

def read_events(path: str | Path, limit: int = 200) -> list[dict]:
    p=Path(path)
    if not p.exists(): return []
    lines=p.read_text(encoding='utf-8',errors='replace').splitlines()[-limit:]
    out=[]
    for line in lines:
        try: out.append(json.loads(line))
        except Exception: continue
    return out
