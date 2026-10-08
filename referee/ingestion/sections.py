from __future__ import annotations
import re
HEADING_PATTERNS = [
    re.compile(r"^(abstract|introduction|background|methods?|materials and methods|results?|discussion|conclusions?|limitations?|references?|supplementary|appendix)\s*$", re.I),
    re.compile(r"^#{1,6}\s+(.+)$"),
    re.compile(r"^(?:\d+(?:\.\d+)*)\s+[A-Z].{2,120}$"),
]
def split_sections(text: str) -> list[dict]:
    lines=text.splitlines(); sections=[]; title='front_matter'; buf=[]; start=1
    def flush(end):
        nonlocal buf,title,start
        body='\n'.join(buf).strip()
        if body or title!='front_matter': sections.append({'title':title.strip(),'start_line':start,'end_line':end,'text':body})
        buf=[]
    for i,line in enumerate(lines,1):
        s=line.strip(); heading=None
        if s:
            for pat in HEADING_PATTERNS:
                m=pat.match(s)
                if m: heading=(m.group(1) if m.groups() else s).strip(); break
        if heading: flush(i-1); title=heading; start=i+1
        else: buf.append(line)
    flush(len(lines)); return sections
def section_index(text: str) -> dict[str,list[dict]]:
    out={}
    for s in split_sections(text): out.setdefault(s['title'].lower(),[]).append(s)
    return out
