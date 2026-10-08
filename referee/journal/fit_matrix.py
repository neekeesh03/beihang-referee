def journal_fit_matrix(classification:dict,profiles:list[dict])->list[dict]:
    text=' '.join(map(str,classification.values())).lower();out=[]
    for p in profiles:
        tags=[str(x).lower() for x in p.get('scope_tags',[])];overlap=sum(t in text for t in tags);out.append({'journal':p.get('name'),'scope_overlap_signals':overlap,'verification_required':True,'notes':p.get('notes','')})
    return sorted(out,key=lambda x:x['scope_overlap_signals'],reverse=True)
