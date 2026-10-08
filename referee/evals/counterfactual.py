from __future__ import annotations
from typing import Any
from .judge import deterministic_judge_a, deterministic_judge_b, deterministic_adjudicate
from .gold import CONCEPTS


def _detected(gold: dict[str,Any], concerns:list[dict], category: str | None = None) -> bool:
    if "required_mechanism_concepts" not in gold and category in CONCEPTS:
        gold={**gold,"defect_id":str(category).upper(),"severity":gold.get("severity","major"),"required_mechanism_concepts":[{"concept":g[0],"acceptable_phrases":g} for g in CONCEPTS[category]],"scientific_consequence":[gold.get("scientific_consequence","")],"acceptable_resolutions":[gold.get("minimum_resolution","")],"forbidden_misdiagnoses":[]}
    for c in concerns:
        a=deterministic_judge_a(gold,c);b=deterministic_judge_b(gold,c);f=deterministic_adjudicate(gold,c,a,b)
        if f.get("mechanism_match")=="yes": return True
    return False


def evaluate_counterfactual_pair(gold: dict[str,Any], category: str, old_concerns: list[dict], new_concerns: list[dict], **_)->dict:
    old=_detected(gold,old_concerns,category);new=_detected(gold,new_concerns,category)
    old_ids={c.get("concern_id") for c in old_concerns};new_ids={c.get("concern_id") for c in new_concerns}
    return {"category":category,"appears_in_defective":old,"disappears_in_fixed":not new,"defect_detection_rate":1.0 if old else 0.0,"repair_recognition_rate":1.0 if not new else 0.0,"causal_sensitivity_pass":old and not new,"persistent_false_concern":bool(new),"unrelated_concern_stability":None,"old_concern_ids":sorted(x for x in old_ids if x),"new_concern_ids":sorted(x for x in new_ids if x)}
