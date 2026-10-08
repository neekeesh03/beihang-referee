def build_citation_graph(records):
    nodes=[];edges=[]
    for i,r in enumerate(records,1):
        rid=getattr(r,'doi',None) or getattr(r,'url',None) or f'R{i:04d}';nodes.append({'id':rid,'title':getattr(r,'title',''),'year':getattr(r,'year',None),'provider':getattr(r,'provider','')});raw=getattr(r,'raw',{}) or {}
        for ref in raw.get('referenced_works',[]) if isinstance(raw,dict) else []:edges.append({'source':rid,'target':ref,'type':'cites'})
    return {'nodes':nodes,'edges':edges}
