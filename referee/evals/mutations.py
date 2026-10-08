import copy
FIELDS=['closure_criterion','scientific_consequence','minimum_resolution','failure_mechanism']
def mutate_concern(concern:dict,seed:int=0)->list[dict]:
    out=[]
    for f in FIELDS:
        c=copy.deepcopy(concern);c[f]='';c['_mutation']=f'remove_{f}';out.append(c)
    c=copy.deepcopy(concern);c['evidence_anchor_ids']=['A_DOES_NOT_EXIST'];c['_mutation']='unknown_anchor';out.append(c)
    c=copy.deepcopy(concern);c['steelman_survives']=False;c['_mutation']='fails_steelman';out.append(c)
    return out
