import re
def lexical_entailment(anchor_text:str,concern_text:str)->dict:
    tok=lambda s:set(re.findall(r'[a-z0-9]{4,}',(s or '').lower()));a=tok(anchor_text);c=tok(concern_text);score=len(a&c)/max(1,len(c))
    return {'score':round(score,3),'label':'supportive' if score>=0.25 else 'weak','method':'lexical_guardrail_not_semantic_proof'}
