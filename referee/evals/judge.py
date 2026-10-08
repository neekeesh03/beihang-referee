from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from ..providers.base import LLMProvider, LLMRequest
from ..contracts.jsoncheck import validate_json_contract



ADDITIONAL_CONCERN_SCHEMA = {
    "type":"object","additionalProperties":False,
    "required":["status","evidence_resolves","mechanism_valid","consequence_proportionate","major_severity_justified","duplicate_of_gold","confidence"],
    "properties":{
        "status":{"enum":["valid_additional","invalid_additional","uncertain_additional","duplicate_of_gold"]},
        "evidence_resolves":{"type":"boolean"},
        "mechanism_valid":{"enum":["yes","no","uncertain"]},
        "consequence_proportionate":{"enum":["yes","no","uncertain"]},
        "major_severity_justified":{"enum":["yes","no","uncertain"]},
        "duplicate_of_gold":{"type":"boolean"},
        "confidence":{"type":"number","minimum":0,"maximum":1},
    },
}

JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["defect_id","mechanism_match","consequence_match","severity_match","resolution_match","generic_only","wrong_mechanism","confidence"],
    "properties": {
        "defect_id": {"type":"string"},
        "mechanism_match": {"enum":["yes","no","uncertain"]},
        "consequence_match": {"enum":["yes","no","uncertain"]},
        "severity_match": {"enum":["yes","no","uncertain"]},
        "resolution_match": {"enum":["yes","no","uncertain"]},
        "generic_only": {"type":"boolean"},
        "wrong_mechanism": {"type":"boolean"},
        "confidence": {"type":"number","minimum":0,"maximum":1},
    },
}

_SYNONYMS = {
    "variable":"feature", "variables":"feature", "screening":"selection", "selected":"selection", "selects":"selection",
    "observations":"dataset", "observation":"dataset", "samples":"dataset", "sample":"dataset",
    "test":"held-out", "testing":"held-out", "validation":"held-out", "folds":"fold", "fold":"fold",
    "affect":"influence", "affects":"influence", "influences":"influence", "influenced":"influence",
    "predictors":"feature", "predictor":"feature", "training":"model", "trained":"model",
    "prior":"before", "preceded":"before", "precedes":"before", "earlier":"before",
    "uncorrected":"nominal", "multiplicity":"multiple", "randomised":"randomized",
}
_STOP = {"the","a","an","and","or","of","to","in","is","are","was","were","be","been","with","by","for","from","that","this","it","its","as","may","can","could","should","would"}


def _tokens(text: Any) -> set[str]:
    raw = re.findall(r"[a-z0-9µ²]+(?:-[a-z0-9]+)?", str(text or "").lower())
    out=set()
    for t in raw:
        if t in _STOP or len(t)<2: continue
        t=_SYNONYMS.get(t,t)
        out.add(t)
    return out


def _phrase_hit(text: str, alternatives: list[str], threshold: float) -> tuple[bool,float]:
    tt=_tokens(text)
    best=0.0
    for alt in alternatives:
        aa=_tokens(alt)
        if not aa: continue
        # Recall-style concept coverage: prediction may contain extra detail.
        score=len(tt & aa)/len(aa)
        best=max(best,score)
        if score>=threshold:
            return True,best
    return False,best


def _field_text(concern: dict[str,Any], *keys: str) -> str:
    return " ".join(str(concern.get(k) or "") for k in keys)


def deterministic_judge_a(gold: dict[str,Any], concern: dict[str,Any]) -> dict[str,Any]:
    mech=_field_text(concern,"title","failure_mechanism")
    hits=[];scores=[]
    for concept in gold.get("required_mechanism_concepts",[]):
        ok,score=_phrase_hit(mech, list(concept.get("acceptable_phrases") or [concept.get("concept","")]), .55)
        hits.append(ok);scores.append(score)
    forbidden=any(_phrase_hit(mech,[x],.75)[0] for x in gold.get("forbidden_misdiagnoses",[]))
    avg_score=sum(scores)/max(1,len(scores))
    mechanism=bool(hits and all(hits) and avg_score>=.65 and not forbidden)
    consequence_text=_field_text(concern,"scientific_consequence")
    consequence=any(_phrase_hit(consequence_text,[x],.42)[0] for x in gold.get("scientific_consequence",[]) if x)
    resolution_text=_field_text(concern,"minimum_resolution","closure_criterion")
    resolution=any(_phrase_hit(resolution_text,[x],.42)[0] for x in gold.get("acceptable_resolutions",[]) if x)
    sev=str(concern.get("severity") or "") == str(gold.get("severity") or "")
    generic=not mechanism and bool(_tokens(mech))
    return {"defect_id":gold["defect_id"],"mechanism_match":"yes" if mechanism else "no","consequence_match":"yes" if consequence else "no","severity_match":"yes" if sev else "no","resolution_match":"yes" if resolution else "no","generic_only":generic,"wrong_mechanism":forbidden or (not mechanism and not generic),"confidence":round(avg_score,3)}


def deterministic_judge_b(gold: dict[str,Any], concern: dict[str,Any]) -> dict[str,Any]:
    # Independently formulated proposition coverage: require each gold concept
    # plus an explicit failure/consequence relation, with a lower phrase threshold
    # but a stronger all-concepts gate.
    mech=_field_text(concern,"failure_mechanism")
    concept_rows=[]
    for concept in gold.get("required_mechanism_concepts",[]):
        ok,score=_phrase_hit(mech, list(concept.get("acceptable_phrases") or [concept.get("concept","")]), .45)
        concept_rows.append((ok,score))
    all_concepts=bool(concept_rows and all(x[0] for x in concept_rows))
    forbidden=any(_phrase_hit(mech,[x],.70)[0] for x in gold.get("forbidden_misdiagnoses",[]))
    avg=sum(x[1] for x in concept_rows)/max(1,len(concept_rows))
    mechanism=all_concepts and avg>=.60 and not forbidden
    consequence_text=_field_text(concern,"scientific_consequence")
    consequence=any(_phrase_hit(consequence_text,[x],.35)[0] for x in gold.get("scientific_consequence",[]) if x)
    resolution_text=_field_text(concern,"minimum_resolution","closure_criterion")
    resolution=any(_phrase_hit(resolution_text,[x],.35)[0] for x in gold.get("acceptable_resolutions",[]) if x)
    sev=str(concern.get("severity") or "") == str(gold.get("severity") or "")
    return {"defect_id":gold["defect_id"],"mechanism_match":"yes" if mechanism else "no","consequence_match":"yes" if consequence else "no","severity_match":"yes" if sev else "no","resolution_match":"yes" if resolution else "no","generic_only":bool(not mechanism and avg>0),"wrong_mechanism":forbidden,"confidence":round(avg,3)}


def deterministic_adjudicate(gold: dict[str,Any], concern: dict[str,Any], a: dict[str,Any], b: dict[str,Any]) -> dict[str,Any]:
    if a["mechanism_match"] == b["mechanism_match"]:
        final=dict(a)
        for k in ("consequence_match","severity_match","resolution_match"):
            if a[k]!=b[k]: final[k]="uncertain"
        final["confidence"]=round((float(a["confidence"])+float(b["confidence"]))/2,3)
    else:
        # Disagreement is conservatively adjudicated by requiring the stricter A
        # mechanism gate. This cannot turn two weak topical matches into a hit.
        final=dict(a)
        final["mechanism_match"]="yes" if a["mechanism_match"]=="yes" and b["confidence"]>=.65 else "uncertain"
        final["confidence"]=round(min(float(a["confidence"]),float(b["confidence"])),3)
    final["adjudicated"]=True
    final["judge_disagreement"]=a["mechanism_match"]!=b["mechanism_match"]
    return final


@dataclass
class ScientificDefectEvaluator:
    llm: LLMProvider | None = None
    judge_model_a: str | None = None
    judge_model_b: str | None = None
    adjudicator_model: str | None = None
    judge_prompt: str = ""
    adjudicator_prompt: str = ""

    async def _model_judge(self, gold: dict[str,Any], concern: dict[str,Any], *, label: str, model: str|None) -> tuple[dict[str,Any],dict[str,Any]]:
        assert self.llm is not None
        ctx=f"benchmark-{label.lower()}-{uuid.uuid4().hex}"
        agent=f"benchmark-judge-{label}"
        out=await self.llm.complete(LLMRequest(operation=f"benchmark_judge_{label}",system=self.judge_prompt,user="PREDICTED CONCERN:\n"+json.dumps(concern,ensure_ascii=False)+"\n\nHIDDEN STRUCTURED GOLD:\n"+json.dumps(gold,ensure_ascii=False),schema=JUDGE_SCHEMA,model=model,temperature=0.0,request_id=uuid.uuid4().hex,context_id=ctx,agent_id=agent))
        if isinstance(out,str): out=json.loads(out)
        errs=validate_json_contract(out,JUDGE_SCHEMA)
        if errs: raise ValueError("benchmark judge schema violation: "+"; ".join(errs))
        return out,{"agent_id":agent,"context_id":ctx,"model":model,"configuration_blinded":True}

    async def evaluate_additional(self, manuscript: str, concern: dict[str,Any]) -> dict[str,Any]:
        """Independently adjudicate an unmatched admitted major concern.

        With no model judge available the result is explicitly uncertain; an
        unmatched concern is never automatically counted as false.
        """
        if self.llm is None:
            return {"final":{"status":"uncertain_additional","evidence_resolves":False,"mechanism_valid":"uncertain","consequence_proportionate":"uncertain","major_severity_justified":"uncertain","duplicate_of_gold":False,"confidence":0.0},"judges":{},"independence":"deterministic_unavailable"}
        async def one(label:str,model:str|None):
            ctx=f"additional-{label.lower()}-{uuid.uuid4().hex}"; agent=f"additional-judge-{label}"
            prompt=("Assess whether this admitted MAJOR concern is scientifically valid against the manuscript itself. "
                    "Do not assume it is false because it was not a planted benchmark defect. Require resolving evidence, a valid failure mechanism, a proportionate consequence, and major-level severity. Return strict JSON only.")
            user_payload="MANUSCRIPT:\n"+manuscript+"\n\nCONCERN:\n"+json.dumps(concern,ensure_ascii=False)
            out=await self.llm.complete(LLMRequest(operation=f"additional_concern_{label}",system=prompt,user=user_payload,schema=ADDITIONAL_CONCERN_SCHEMA,model=model,temperature=0.0,request_id=uuid.uuid4().hex,context_id=ctx,agent_id=agent))
            if isinstance(out,str): out=json.loads(out)
            errs=validate_json_contract(out,ADDITIONAL_CONCERN_SCHEMA)
            if errs: raise ValueError("additional concern judge schema violation: "+"; ".join(errs))
            return out,{"agent_id":agent,"context_id":ctx,"model":model,"configuration_blinded":True}
        a,ia=await one("A",self.judge_model_a); b,ib=await one("B",self.judge_model_b)
        if a["status"]==b["status"]:
            final=dict(a); final["confidence"]=round((float(a["confidence"])+float(b["confidence"]))/2,3)
        else:
            # disagreement is never converted into a false positive automatically
            final={"status":"uncertain_additional","evidence_resolves":a["evidence_resolves"] and b["evidence_resolves"],"mechanism_valid":"uncertain","consequence_proportionate":"uncertain","major_severity_justified":"uncertain","duplicate_of_gold":a["duplicate_of_gold"] or b["duplicate_of_gold"],"confidence":round(min(float(a["confidence"]),float(b["confidence"])),3)}
        return {"final":final,"judges":{"A":ia,"B":ib},"independence":"fresh_blinded_contexts"}

    async def evaluate(self, gold: dict[str,Any], concern: dict[str,Any]) -> dict[str,Any]:
        # Deterministic hidden-concept screen is always recorded. It is not the
        # sole correctness criterion for an official campaign; two independent
        # blinded evaluators still assess the full scientific mechanism.
        concept_a=deterministic_judge_a(gold,concern)
        concept_b=deterministic_judge_b(gold,concern)
        concept_screen=deterministic_adjudicate(gold,concern,concept_a,concept_b)
        if self.llm is None:
            a=concept_a; b=concept_b
            final=concept_screen
            identities={"A":{"type":"deterministic-concept-a"},"B":{"type":"deterministic-proposition-b"},"adjudicator":{"type":"deterministic-conservative"}}
        else:
            a,ia=await self._model_judge(gold,concern,label="A",model=self.judge_model_a)
            b,ib=await self._model_judge(gold,concern,label="B",model=self.judge_model_b)
            if a["mechanism_match"]==b["mechanism_match"] and a["consequence_match"]==b["consequence_match"]:
                final=deterministic_adjudicate(gold,concern,a,b); ic={"type":"not_needed"}
            else:
                ctx=f"benchmark-adjudicator-{uuid.uuid4().hex}"; agent="benchmark-adjudicator"
                payload={"predicted_concern":concern,"hidden_gold":gold,"judge_a":a,"judge_b":b}
                out=await self.llm.complete(LLMRequest(operation="benchmark_adjudication",system=self.adjudicator_prompt,user=json.dumps(payload,ensure_ascii=False),schema=JUDGE_SCHEMA,model=self.adjudicator_model,temperature=0.0,request_id=uuid.uuid4().hex,context_id=ctx,agent_id=agent))
                if isinstance(out,str): out=json.loads(out)
                errs=validate_json_contract(out,JUDGE_SCHEMA)
                if errs: raise ValueError("benchmark adjudicator schema violation: "+"; ".join(errs))
                final={**out,"adjudicated":True,"judge_disagreement":True}; ic={"agent_id":agent,"context_id":ctx,"model":self.adjudicator_model,"configuration_blinded":True}
            identities={"A":ia,"B":ib,"adjudicator":ic}
        return {"deterministic_concept_screen":concept_screen,"judge_a":a,"judge_b":b,"final":final,"identities":identities,"configuration_hidden":True}
