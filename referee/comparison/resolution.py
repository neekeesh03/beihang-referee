def build_resolution_matrix(prior_concerns:list[dict],current_text:str)->list[dict]:
    out=[];low=current_text.lower()
    for c in prior_concerns:
        criterion=(c.get('closure_criterion') or '').strip();signals=[w for w in criterion.lower().split() if len(w)>6][:6];hits=sum(w in low for w in signals)
        out.append({'concern_id':c.get('concern_id'),'title':c.get('title'),'closure_criterion':criterion,'textual_resolution_signal':'possible' if signals and hits>=max(1,len(signals)//2) else 'not_demonstrated','requires_scientific_reassessment':True})
    return out
