from .normalize import normalize_title,normalize_doi
def deduplicate_records(records):
    seen={};out=[]
    for r in records:
        doi=normalize_doi(getattr(r,'doi',None));key=('doi',doi) if doi else ('title',normalize_title(getattr(r,'title',''))[:220],getattr(r,'year',None))
        if key in seen:
            prev=seen[key]
            if not getattr(prev,'abstract',None) and getattr(r,'abstract',None):prev.abstract=r.abstract
            continue
        seen[key]=r;out.append(r)
    return out
