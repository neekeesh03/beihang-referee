import json
from pathlib import Path
from ..validation import validate_major_comment
def evaluate_cases(path):
    cases=json.loads(Path(path).read_text(encoding='utf-8'));rows=[]
    for c in cases:
        errors=validate_major_comment(c['concern'],set(c.get('known_anchors',[])));pred=not errors;gold=bool(c['expected_admissible']);rows.append({'id':c['id'],'gold':gold,'pred':pred,'errors':errors,'pass':gold==pred})
    return {'total':len(rows),'passed':sum(r['pass'] for r in rows),'rows':rows}
