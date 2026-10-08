import math
from .normalize import normalize_title
def _tokens(s):return set(normalize_title(s).split())
def rank_records(records,query:str,current_year:int|None=None):
    q=_tokens(query);scored=[]
    for r in records:
        t=_tokens(getattr(r,'title',''));overlap=len(q&t)/max(1,len(q|t));cites=getattr(r,'citation_count',None) or 0;citation=math.log1p(cites)/10;recency=0
        if current_year and getattr(r,'year',None):recency=max(0,1-(current_year-r.year)/20)/5
        scored.append((overlap+citation+recency,r))
    return [r for _,r in sorted(scored,key=lambda x:x[0],reverse=True)]
