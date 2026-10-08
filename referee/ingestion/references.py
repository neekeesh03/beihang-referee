from __future__ import annotations
import re
DOI=re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+",re.I)
PMID=re.compile(r"\bPMID\s*[: ]\s*(\d{6,9})\b",re.I)
ARXIV=re.compile(r"\barXiv\s*[: ]\s*(\d{4}\.\d{4,5}(?:v\d+)?)",re.I)
URL=re.compile(r"https?://[^\s>)\]}]+",re.I)
YEAR=re.compile(r"\b(?:19|20)\d{2}\b")
def extract_reference_signals(text:str)->dict:
    dois=sorted({m.group(0).rstrip('.,;') for m in DOI.finditer(text)})
    pmids=sorted({m.group(1) for m in PMID.finditer(text)})
    arxiv=sorted({m.group(1) for m in ARXIV.finditer(text)})
    urls=sorted({m.group(0).rstrip('.,;') for m in URL.finditer(text)})
    years=[int(m.group(0)) for m in YEAR.finditer(text)]
    return {'dois':dois,'pmids':pmids,'arxiv_ids':arxiv,'urls':urls,'year_min':min(years) if years else None,'year_max':max(years) if years else None}
