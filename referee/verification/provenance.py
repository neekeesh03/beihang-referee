def provenance_score(concern:dict,anchor_by_id:dict)->dict:
    ids=concern.get('evidence_anchor_ids') or [];found=[anchor_by_id.get(i) for i in ids if anchor_by_id.get(i)];scores=[]
    for a in found:
        s=1
        if a.get('document_id'):s+=1
        if a.get('locator'):s+=1
        if a.get('quote_or_fact'):s+=1
        if a.get('confidence')=='high':s+=1
        scores.append(s/5)
    avg=sum(scores)/len(scores) if scores else 0
    return {'concern_id':concern.get('concern_id'),'anchor_count':len(ids),'resolved_anchor_count':len(found),'score':round(avg,3),'grade':'high' if avg>=.8 else 'moderate' if avg>=.5 else 'low'}
