import re
NEG={'no','not','without','failed','none','neither','lack','lacks','absence'}
def contradiction_signal(a:str,b:str)->dict:
    ta=set(re.findall(r'\b\w+\b',(a or '').lower()));tb=set(re.findall(r'\b\w+\b',(b or '').lower()));shared=len((ta-NEG)&(tb-NEG));neg_a=bool(ta&NEG);neg_b=bool(tb&NEG)
    return {'possible_contradiction':shared>=3 and neg_a!=neg_b,'shared_content_tokens':shared,'negation_mismatch':neg_a!=neg_b}
