from __future__ import annotations
import re
from pathlib import Path
def inspect_latex(path:str|Path)->dict:
    p=Path(path); text=p.read_text(encoding='utf-8',errors='replace')
    labels=set(re.findall(r"\\label\{([^}]+)\}",text)); refs=re.findall(r"\\(?:ref|eqref)\{([^}]+)\}",text)
    cites=[c.strip() for grp in re.findall(r"\\cite\w*\{([^}]+)\}",text) for c in grp.split(',')]
    graphics=re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}",text)
    bibs=re.findall(r"\\bibliography\{([^}]+)\}",text)
    return {'path':str(p),'labels':sorted(labels),'references':refs,'unresolved_refs':sorted({r for r in refs if r not in labels}),'citations':sorted(set(cites)),'graphics':graphics,'bibliography_files':bibs,'display_math_blocks':len(re.findall(r'\\\[|\\begin\{equation',text))}
