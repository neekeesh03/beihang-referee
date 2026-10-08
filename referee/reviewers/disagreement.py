def disagreement_map(specialist_results:dict)->dict:
    positions={}
    for task,p in specialist_results.items():
        agent=p.get('specialist','unknown');r=p.get('result') or {};positions[agent]={'concern_titles':[c.get('title') for c in r.get('concerns',[])],'uncertainty':r.get('uncertainty',[]),'notes':r.get('notes',[])}
    return {'positions':positions,'reviewer_count':len(positions),'requires_adjudication':len(positions)>1 and len({tuple(v['concern_titles']) for v in positions.values()})>1}
