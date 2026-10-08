from __future__ import annotations
import tempfile
import time
from pathlib import Path
from typing import Callable, Any
from .scoring import aggregate
from .judge import deterministic_judge_a, deterministic_judge_b, deterministic_adjudicate
from .gold import structured_gold_for_case


def _gold(case: dict[str, Any]):
    return case.get("structured_gold") or structured_gold_for_case(case)


def _judge_concern(gold: dict[str,Any], concern: dict[str,Any]) -> dict[str,Any]:
    a=deterministic_judge_a(gold,concern)
    b=deterministic_judge_b(gold,concern)
    final=deterministic_adjudicate(gold,concern,a,b)
    return {"judge_a":a,"judge_b":b,"final":final}


def _best_match(gold: dict[str,Any] | None, concerns: list[dict[str,Any]]):
    if not gold: return None,None
    rows=[]
    for c in concerns:
        j=_judge_concern(gold,c)
        f=j["final"]
        # Mechanism correctness is the only route to detection. Confidence only
        # breaks ties; topical similarity is never a correctness criterion.
        rank=(1 if f.get("mechanism_match")=="yes" else 0, float(f.get("confidence") or 0))
        rows.append((rank,c,j))
    if not rows:return None,None
    rows.sort(key=lambda x:x[0],reverse=True)
    return rows[0][1],rows[0][2]


def evaluate_state(case: dict[str, Any], state) -> dict[str, Any]:
    concerns=list(state.admitted_concerns)
    gold=_gold(case)
    match,judgment=_best_match(gold,concerns)
    final=(judgment or {}).get("final",{})
    detected=bool(gold and match and final.get("mechanism_match")=="yes")
    anchor_ids={a.get("anchor_id") for a in state.evidence_anchors if isinstance(a,dict)}
    claim_ids={c.get("claim_id") for c in state.claims if isinstance(c,dict)}
    anchor_refs=[a for c in concerns for a in c.get("evidence_anchor_ids",[])]
    claim_refs=[x for c in concerns for x in c.get("claim_ids",[])]
    entailment_rows=[]
    for c in concerns:
        ent=((c.get("provenance_gate") or {}).get("entailment") or {}).get("status")
        if ent is not None: entailment_rows.append(1.0 if ent=="supported" else 0.0)
    predicted_major=len(concerns);valid_predictions=1 if detected else 0
    false_major=max(0,predicted_major-valid_predictions);ccore_case=not bool(gold)
    scientific_correct=detected if gold else predicted_major==0
    mechanism=1.0 if detected else (0.0 if gold else None)
    consequence=(1.0 if final.get("consequence_match")=="yes" else 0.0) if gold and judgment else (0.0 if gold else None)
    closure=(1.0 if final.get("resolution_match")=="yes" else 0.0) if gold and judgment else (0.0 if gold else None)
    severity=(final.get("severity_match") if judgment else None)
    return {
        "case_id":case.get("case_id"),"domain":case.get("domain"),"category":case.get("category"),
        "has_gold_defect":bool(gold),"detected":detected,"structured_gold_used":bool(gold),
        "gold_severity":(gold or {}).get("severity") or case.get("expected_severity"),
        "pred_severity":match.get("severity") if detected else "none",
        "severity_match":severity,
        "predicted_major_count":predicted_major,"false_major_count":false_major,
        "ccore_case_false_positive":bool(ccore_case and predicted_major>0),
        "anchor_validity":(sum(a in anchor_ids for a in anchor_refs)/len(anchor_refs)) if anchor_refs else None,
        "claim_id_validity":(sum(x in claim_ids for x in claim_refs)/len(claim_refs)) if claim_refs else None,
        "evidence_entailment_pass_rate":(sum(entailment_rows)/len(entailment_rows)) if entailment_rows else None,
        "mechanism_correctness":mechanism,"consequence_correctness":consequence,"closure_quality":closure,
        "benchmark_judgment":judgment,
        "confidence":match.get("reviewer_confidence") if detected else None,"correct":scientific_correct,
        "llm_calls":state.metrics.get("llm_calls",0),"search_calls":state.metrics.get("search_calls",0),
        "citation_metrics":state.metrics.get("citation_metrics",{}),
        "run_status":getattr(state,"status",None),
        "final_review_exportable":getattr(state,"final_review_exportable",None),
        "hard_invariant_failure_count":len(getattr(state,"hard_invariant_failures",[]) or []),
    }


async def evaluate_state_independent(case: dict[str, Any], state, evaluator) -> dict[str, Any]:
    """Evaluate a completed review with blinded independent judges.

    Gold matching establishes whether the planted defect was detected. Every
    *unmatched* admitted major concern is separately adjudicated against the
    manuscript, so unmatched does not mean false. Clean controls use the same
    concern-validity adjudication.
    """
    base=evaluate_state(case,state)
    gold=_gold(case)
    concerns=list(state.admitted_concerns)
    manuscript=str(case.get("manuscript") or case.get("text") or "")
    rows=[]
    if gold:
        for c in concerns:
            rows.append((c,await evaluator.evaluate(gold,c)))
        positives=[x for x in rows if (x[1].get("final") or {}).get("mechanism_match")=="yes"]
        if positives:
            positives.sort(key=lambda x:float((x[1].get("final") or {}).get("confidence") or 0),reverse=True)
            match,judgment=positives[0];detected=True
        else:
            match,judgment=(rows[0] if rows else (None,None));detected=False
    else:
        match=judgment=None;detected=False
    final=(judgment or {}).get("final",{})
    matched_id=match.get("concern_id") if match else None
    additional=[]
    for c in concerns:
        if matched_id and c.get("concern_id")==matched_id:
            continue
        aj=await evaluator.evaluate_additional(manuscript,c)
        additional.append({"concern_id":c.get("concern_id"),"judgment":aj})
    statuses=[((x.get("judgment") or {}).get("final") or {}).get("status") for x in additional]
    valid_additional=sum(x=="valid_additional" for x in statuses)
    invalid_additional=sum(x=="invalid_additional" for x in statuses)
    uncertain_additional=sum(x=="uncertain_additional" for x in statuses)
    duplicate_additional=sum(x=="duplicate_of_gold" for x in statuses)
    gold_valid=1 if (detected and final.get("consequence_match")=="yes" and final.get("severity_match")=="yes") else 0
    scientifically_valid_major=gold_valid+valid_additional
    scientifically_invalid_major=invalid_additional
    precision_den=scientifically_valid_major+scientifically_invalid_major
    ccore_case=not bool(gold)
    base.update({
        "detected":detected,
        "mechanism_correctness":1.0 if detected else (0.0 if gold else None),
        "consequence_correctness":1.0 if final.get("consequence_match")=="yes" else (0.0 if gold and judgment else None),
        "closure_quality":1.0 if final.get("resolution_match")=="yes" else (0.0 if gold and judgment else None),
        "pred_severity":match.get("severity") if detected and match else "none",
        "confidence":match.get("reviewer_confidence") if detected and match else None,
        "correct":detected if gold else scientifically_invalid_major==0 and uncertain_additional==0,
        "validated_major_count":scientifically_valid_major,
        "invalid_major_count":scientifically_invalid_major,
        "uncertain_major_count":uncertain_additional,
        "duplicate_major_count":duplicate_additional,
        "false_major_count":scientifically_invalid_major,
        "major_precision_denominator":precision_den,
        "ccore_case_false_positive":bool(ccore_case and scientifically_invalid_major>0),
        "ccore_control_adjudication_complete":bool(ccore_case and uncertain_additional==0),
        "benchmark_judgment":judgment,
        "all_benchmark_judgments":[{"concern_id":c.get("concern_id"),"judgment":j} for c,j in rows],
        "additional_concern_judgments":additional,
        "independent_benchmark_judging":{"status":"completed","configuration_hidden":True,"unmatched_concerns_independently_adjudicated":True},
    })
    return base


async def run_end_to_end_cases(cases: list[dict[str, Any]], engine_factory: Callable[[Path], Any], *, keep_runs: bool=False, evaluator=None) -> dict[str, Any]:
    rows=[]
    with tempfile.TemporaryDirectory(prefix="referee-e2e-") as td:
        base=Path(td)
        for i,case in enumerate(cases,1):
            manuscript=case.get("manuscript") or case.get("text")
            if manuscript is None: continue
            p=base/f"case-{i:05d}.md";p.write_text(manuscript,encoding="utf-8")
            engine=engine_factory(base/"runs")
            started=time.perf_counter()
            state=await engine.review([str(p)],query="Hidden-gold benchmark review",run_id=f"case-{i:05d}")
            row=(await evaluate_state_independent(case,state,evaluator) if evaluator is not None else evaluate_state(case,state));row["latency_seconds"]=time.perf_counter()-started;rows.append(row)
        result={"metrics":aggregate(rows),"cases":rows,"gold_hidden_from_review_pipeline":True,"lexical_similarity_used_for_detection":False,"independent_evaluator_enabled":evaluator is not None}
        if keep_runs: result["run_root"]=str(base/"runs")
        return result

async def evaluate_severity_state_independent(case: dict[str,Any], state, evaluator) -> dict[str,Any]:
    """Evaluate major/minor/observation discrimination on dedicated calibration cases."""
    gold=case.get("structured_gold") or _gold(case)
    candidates=[]
    for c in list(state.admitted_concerns):
        candidates.append({**c,"severity":"major"})
    for c in list((state.final_review or {}).get("minor_comments") or []):
        if isinstance(c,dict): candidates.append({**c,"severity":"minor","failure_mechanism":c.get("failure_mechanism") or c.get("issue") or c.get("text") or c.get("title") or "","scientific_consequence":c.get("scientific_consequence") or c.get("consequence") or "","minimum_resolution":c.get("minimum_resolution") or c.get("resolution") or "","closure_criterion":c.get("closure_criterion") or c.get("resolution") or ""})
    for c in list((state.final_review or {}).get("observations") or []):
        if isinstance(c,dict): candidates.append({**c,"severity":"observation","failure_mechanism":c.get("failure_mechanism") or c.get("text") or c.get("observation") or c.get("title") or "","scientific_consequence":c.get("scientific_consequence") or "no material scientific consequence","minimum_resolution":c.get("minimum_resolution") or "optional clarification","closure_criterion":c.get("closure_criterion") or "optional"})
        elif c: candidates.append({"severity":"observation","failure_mechanism":str(c),"scientific_consequence":"no material scientific consequence","minimum_resolution":"optional clarification","closure_criterion":"optional"})
    judged=[]
    for c in candidates:
        judged.append((c,await evaluator.evaluate(gold,c)))
    matches=[x for x in judged if (x[1].get("final") or {}).get("mechanism_match")=="yes"]
    matches.sort(key=lambda x:float((x[1].get("final") or {}).get("confidence") or 0),reverse=True)
    match,judgment=(matches[0] if matches else (None,None))
    pred=match.get("severity") if match else "none"
    expected=str(gold.get("severity") or case.get("expected_severity") or "none")
    return {"case_id":case.get("case_id"),"domain":case.get("domain") or "severity_calibration","category":case.get("category"),"has_gold_defect":True,"detected":bool(match),"gold_severity":expected,"pred_severity":pred,"severity_match":"yes" if pred==expected else "no","severity_correct":pred==expected,"mechanism_correctness":1.0 if match else 0.0,"consequence_correctness":1.0 if match and (judgment.get("final") or {}).get("consequence_match")=="yes" else 0.0,"closure_quality":1.0 if match and (judgment.get("final") or {}).get("resolution_match")=="yes" else 0.0,"predicted_major_count":sum(c.get("severity")=="major" for c in candidates),"validated_major_count":1 if match and pred=="major" else 0,"invalid_major_count":sum(c.get("severity")=="major" for c in candidates)-(1 if match and pred=="major" else 0),"uncertain_major_count":0,"false_major_count":max(0,sum(c.get("severity")=="major" for c in candidates)-(1 if match and pred=="major" else 0)),"ccore_case_false_positive":False,"benchmark_judgment":judgment,"run_status":state.status,"hard_invariant_failure_count":len(getattr(state,"hard_invariant_failures",[]) or []),"llm_calls":state.metrics.get("llm_calls",0),"search_calls":state.metrics.get("search_calls",0),"citation_metrics":state.metrics.get("citation_metrics",{})}
