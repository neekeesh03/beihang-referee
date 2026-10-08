from collections import defaultdict
def consensus_summary(specialist_results:dict)->dict:
    clusters=defaultdict(list)
    for task,payload in specialist_results.items():
        agent=payload.get('specialist','unknown');result=payload.get('result') or {}
        for c in result.get('concerns',[]):
            key=(c.get('title','').strip().lower(),tuple(sorted(c.get('claim_ids') or [])));clusters[key].append({'agent':agent,'concern':c})
    items=[]
    for (title,claim_ids),members in clusters.items():items.append({'title':title,'claim_ids':list(claim_ids),'reviewer_count':len({m['agent'] for m in members}),'reviewers':sorted({m['agent'] for m in members}),'members':members})
    return {'clusters':sorted(items,key=lambda x:x['reviewer_count'],reverse=True),'cluster_count':len(items)}
