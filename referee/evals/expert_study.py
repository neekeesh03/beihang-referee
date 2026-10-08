from __future__ import annotations
import hashlib,json,random
from pathlib import Path

def prepare_blinded_study(system_outputs:dict[str,list[dict]],out_dir:str|Path,*,seed:int=17)->dict:
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);rng=random.Random(seed);assignments=[];codebook=[]
    items=[]
    for source,concerns in system_outputs.items():
        for i,c in enumerate(concerns):items.append((source,i,c))
    rng.shuffle(items)
    for n,(source,i,c) in enumerate(items,1):
        blinded=f"B{n:05d}";assignments.append({'blinded_id':blinded,'concern':c,'ratings':{'factually_correct':None,'evidence_grounded':None,'scientifically_important':None,'severity_appropriate':None,'actionable':None,'non_redundant':None,'useful_to_authors':None,'include_in_review':None}});codebook.append({'blinded_id':blinded,'source':source,'source_index':i})
    (out/'blinded_items.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in assignments)+'\n',encoding='utf-8')
    (out/'source_codebook.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in codebook)+'\n',encoding='utf-8')
    return {'items':len(assignments),'blinded_items':str(out/'blinded_items.jsonl'),'codebook':str(out/'source_codebook.jsonl'),'seed':seed}
