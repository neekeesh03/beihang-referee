from __future__ import annotations

import json
import re
import tempfile
import time
from pathlib import Path
from typing import Callable, Any

from .corpus import load_corpus
from .end_to_end import evaluate_state, evaluate_state_independent, evaluate_severity_state_independent
from .scoring import aggregate
from .judge import deterministic_judge_a, deterministic_judge_b, deterministic_adjudicate


def _status_from_closure(obj: Any) -> str:
    allowed={"resolved","partially_resolved","unresolved","not_assessable"}
    if isinstance(obj, dict):
        for k in ("resolution_status","status","closure_status"):
            v=str(obj.get(k,"")).lower()
            if v in allowed:return v
            if v in {"closed","verified","complete"}:return "resolved"
            if v in {"open","not_resolved"}:return "unresolved"
            if v in {"partial"}:return "partially_resolved"
        for v in obj.values():
            s=_status_from_closure(v)
            if s!="unknown":return s
    if isinstance(obj,list):
        vals=[_status_from_closure(x) for x in obj]
        vals=[v for v in vals if v!="unknown"]
        if len(vals)==1:return vals[0]
        if vals and all(v=="resolved" for v in vals):return "resolved"
        if "unresolved" in vals:return "unresolved"
        if "partially_resolved" in vals:return "partially_resolved"
    return "unknown"


def _rebuttal_row(out:dict[str,Any])->dict[str,Any]:
    rows=out.get("rows") or []
    return rows[0] if rows and isinstance(rows[0],dict) else {}


def _rebuttal_metrics(rows:list[dict[str,Any]])->dict[str,Any]:
    n=len(rows);resolved=[r for r in rows if r.get("expected")=="resolved"]
    nonresolved=[r for r in rows if r.get("expected") in {"unresolved","partially_resolved","not_assessable"}]
    partial=[r for r in rows if r.get("expected")=="partially_resolved"]
    promise=[r for r in rows if r.get("expected_promise_without_change")]
    evidence=[r for r in rows if r.get("expected_response_without_evidence")]
    regress=[r for r in rows if r.get("expected_new_regression")]
    return {
        "cases":n,
        "resolution_status_accuracy":round(sum(r.get("correct",False) for r in rows)/max(1,n),4),
        "false_closure_rate":round(sum(r.get("predicted")=="resolved" and r.get("expected")!="resolved" for r in rows)/max(1,len(nonresolved)),4),
        "missed_closure_rate":round(sum(r.get("expected")=="resolved" and r.get("predicted")!="resolved" for r in rows)/max(1,len(resolved)),4),
        "partial_resolution_accuracy":round(sum(r.get("predicted")=="partially_resolved" for r in partial)/max(1,len(partial)),4) if partial else None,
        "promise_without_change_recall":round(sum(r.get("pred_promise_without_change") for r in promise)/max(1,len(promise)),4) if promise else None,
        "response_without_evidence_recall":round(sum(r.get("pred_response_without_evidence") for r in evidence)/max(1,len(evidence)),4) if evidence else None,
        "regression_detection_rate":round(sum(r.get("pred_new_regression") for r in regress)/max(1,len(regress)),4) if regress else None,
    }


def _repeatability(rows:list[dict[str,Any]], repeats:int)->dict[str,Any]:
    out={"repeats":max(1,repeats),"detection_agreement":None,"severity_agreement":None,"stable_true_positive":0,"unstable_true_positive":0,"stable_false_positive":0,"unstable_false_positive":0,"stable_true_negative":0,"stable_false_negative":0}
    if repeats<=1:return out
    grouped={}
    for r in rows:grouped.setdefault((r.get("corpus"),r.get("case_id")),[]).append(r)
    complete=[v for v in grouped.values() if len(v)==repeats]
    out["cases_with_complete_repeats"]=len(complete)
    out["detection_agreement"]=round(sum(len({bool(x.get("detected")) for x in v})==1 for v in complete)/max(1,len(complete)),4)
    out["severity_agreement"]=round(sum(len({x.get("pred_severity") for x in v})==1 for v in complete)/max(1,len(complete)),4)
    for v in complete:
        if v[0].get("has_gold_defect"):
            flags=[bool(x.get("detected")) for x in v]
            if all(flags):out["stable_true_positive"]+=1
            elif any(flags):out["unstable_true_positive"]+=1
            else:out["stable_false_negative"]+=1
        else:
            flags=[bool(x.get("ccore_case_false_positive")) for x in v]
            if all(flags):out["stable_false_positive"]+=1
            elif any(flags):out["unstable_false_positive"]+=1
            else:out["stable_true_negative"]+=1
    return out


def _mechanism_hit(gold:dict[str,Any],c:dict[str,Any])->bool:
    a=deterministic_judge_a(gold,c);b=deterministic_judge_b(gold,c);f=deterministic_adjudicate(gold,c,a,b)
    return f.get("mechanism_match")=="yes"


def _signature(c:dict[str,Any])->str:
    return re.sub(r"\s+"," ",(str(c.get("title",''))+" "+str(c.get("failure_mechanism",''))).lower()).strip()


def _counterfactual_row(pair:dict[str,Any],gold_case:dict[str,Any],old_state,new_state)->dict[str,Any]:
    gold=gold_case.get("structured_gold")
    old=list(old_state.admitted_concerns);new=list(new_state.admitted_concerns)
    old_hit=any(_mechanism_hit(gold,c) for c in old) if gold else False
    new_hit=any(_mechanism_hit(gold,c) for c in new) if gold else False
    old_other={_signature(c) for c in old if not (gold and _mechanism_hit(gold,c))}
    new_other={_signature(c) for c in new if not (gold and _mechanism_hit(gold,c))}
    stability=len(old_other & new_other)/max(1,len(old_other | new_other)) if (old_other or new_other) else 1.0
    return {"pair_id":pair.get("pair_id"),"category":gold_case.get("category"),"defect_detected_in_defective":old_hit,"repair_recognized":not new_hit,"causal_sensitivity_pass":old_hit and not new_hit,"persistent_false_concern":new_hit,"unrelated_concern_stability":round(stability,4)}


def _counterfactual_metrics(rows:list[dict[str,Any]])->dict[str,Any]:
    n=len(rows)
    return {"pairs":n,"defect_detection_rate":round(sum(r["defect_detected_in_defective"] for r in rows)/max(1,n),4),"repair_recognition_rate":round(sum(r["repair_recognized"] for r in rows)/max(1,n),4),"causal_sensitivity_pass_rate":round(sum(r["causal_sensitivity_pass"] for r in rows)/max(1,n),4),"persistent_false_concern_rate":round(sum(r["persistent_false_concern"] for r in rows)/max(1,n),4),"mean_unrelated_concern_stability":round(sum(r["unrelated_concern_stability"] for r in rows)/max(1,n),4)}


async def run_full_suite(engine_factory: Callable[[str, Path], Any], *, root: str|Path|None=None, limit_per_corpus: int|None=None, repeats: int=1, run_counterfactuals: bool=True, evaluator=None) -> dict[str,Any]:
    """Run hidden-gold initial, revision, rebuttal and counterfactual validation.

    Gold is loaded only after each review state is produced; the review engine
    receives manuscript/revision/rebuttal material, never structured gold.
    """
    scientific=load_corpus("scientific",root);domain=load_corpus("domain",root);revision=load_corpus("revision",root);rebuttal=load_corpus("rebuttal",root);severity_cases=load_corpus("severity",root)
    if limit_per_corpus is not None:
        scientific=scientific[:limit_per_corpus];domain=domain[:limit_per_corpus];revision=revision[:limit_per_corpus];rebuttal=rebuttal[:limit_per_corpus];severity_cases=severity_cases[:limit_per_corpus]
    source={r["case_id"]:r for r in load_corpus("scientific",root)}
    initial_rows=[];revision_rows=[];rebuttal_rows=[];counterfactual_rows=[]
    with tempfile.TemporaryDirectory(prefix="referee-full-benchmark-") as td:
        base=Path(td)
        for corpus_name,cases in (("scientific",scientific),("domain",domain)):
            for i,case in enumerate(cases):
                p=base/f"{corpus_name}-{i}.md";p.write_text(case["manuscript"],encoding="utf-8")
                for rep in range(1,max(1,repeats)+1):
                    engine=engine_factory("initial",base/"runs");t=time.perf_counter()
                    state=await engine.review([str(p)],query="Hidden-gold scientific benchmark",run_id=f"{corpus_name}-{i}-r{rep}")
                    row=(await evaluate_state_independent(case,state,evaluator) if evaluator is not None else evaluate_state(case,state));row["latency_seconds"]=time.perf_counter()-t;row["corpus"]=corpus_name;row["repeat"]=rep;initial_rows.append(row)
        for i,case in enumerate(severity_cases):
            p=base/f"severity-{i}.md";p.write_text(case["manuscript"],encoding="utf-8")
            engine=engine_factory("initial",base/"runs");t=time.perf_counter()
            state=await engine.review([str(p)],query="Hidden-gold severity calibration benchmark",run_id=f"severity-{i}")
            row=(await evaluate_severity_state_independent(case,state,evaluator) if evaluator is not None else evaluate_state(case,state));row["latency_seconds"]=time.perf_counter()-t;row["corpus"]="severity";row["repeat"]=1;initial_rows.append(row)
        for i,pair in enumerate(revision):
            old=base/f"rev-{i}-old.md";new=base/f"rev-{i}-new.md";prior=base/f"rev-{i}-concerns.json"
            old.write_text(pair["old_text"],encoding="utf-8");new.write_text(pair["new_text"],encoding="utf-8")
            source_case=source.get(pair.get("source_case")) or {}; prior_gold=source_case.get("gold_concern")
            prior.write_text(json.dumps([prior_gold] if prior_gold else [],ensure_ascii=False),encoding="utf-8")
            engine=engine_factory("revision",base/"runs");t=time.perf_counter()
            state=await engine.review([str(new)],query="Hidden-gold revision benchmark",mode_inputs={"prior_manuscript":str(old),"prior_concerns":str(prior)})
            predicted=_status_from_closure(state.mode_artifacts.get("revision_closure",{}));expected=str(pair.get("expected_resolution") or "unresolved")
            revision_rows.append({"case_id":pair["pair_id"],"expected":expected,"predicted":predicted,"correct":predicted==expected,"latency_seconds":time.perf_counter()-t,"llm_calls":state.metrics.get("llm_calls",0),"run_status":state.status,"hard_invariant_failure_count":len(state.hard_invariant_failures)})
            if run_counterfactuals and source_case.get("structured_gold"):
                old_engine=engine_factory("initial",base/"runs");new_engine=engine_factory("initial",base/"runs")
                old_state=await old_engine.review([str(old)],query="Counterfactual defective version",run_id=f"cf-{i}-old")
                new_state=await new_engine.review([str(new)],query="Counterfactual repaired version",run_id=f"cf-{i}-new")
                
                if evaluator is not None:
                    old_eval=await evaluate_state_independent(source_case,old_state,evaluator)
                    new_eval=await evaluate_state_independent(source_case,new_state,evaluator)
                    old=list(old_state.admitted_concerns); new=list(new_state.admitted_concerns)
                    gold=source_case.get("structured_gold")
                    old_other={_signature(c) for c in old if not (gold and _mechanism_hit(gold,c))}
                    new_other={_signature(c) for c in new if not (gold and _mechanism_hit(gold,c))}
                    stability=len(old_other & new_other)/max(1,len(old_other | new_other)) if (old_other or new_other) else 1.0
                    counterfactual_rows.append({"pair_id":pair.get("pair_id"),"category":source_case.get("category"),"defect_detected_in_defective":bool(old_eval.get("detected")),"repair_recognized":not bool(new_eval.get("detected")),"causal_sensitivity_pass":bool(old_eval.get("detected")) and not bool(new_eval.get("detected")),"persistent_false_concern":bool(new_eval.get("detected")),"unrelated_concern_stability":round(stability,4),"independent_judging":True})
                else:
                    counterfactual_rows.append(_counterfactual_row(pair,source_case,old_state,new_state))
        for i,case in enumerate(rebuttal):
            manuscript=base/f"reb-{i}-paper.md";comments=base/f"reb-{i}-comments.md";response=base/f"reb-{i}-response.md"
            manuscript.write_text(case.get("revised_manuscript") or "",encoding="utf-8")
            comments.write_text(case.get("reviewer_comment") or "",encoding="utf-8")
            response.write_text(case.get("author_response") or case.get("response_text") or "",encoding="utf-8")
            engine=engine_factory("rebuttal",base/"runs");t=time.perf_counter()
            state=await engine.review([str(manuscript)],query="Hidden-gold rebuttal benchmark",mode_inputs={"reviewer_comments":str(comments),"rebuttal":str(response)})
            closure=state.mode_artifacts.get("rebuttal_closure",{});row=_rebuttal_row(closure);pred=_status_from_closure(row)
            pred_reg=bool(closure.get("new_regressions"));expected=str(case.get("expected_resolution_status") or "not_assessable")
            rebuttal_rows.append({"case_id":case["case_id"],"expected":expected,"predicted":pred,"correct":pred==expected,"expected_promise_without_change":bool(case.get("promise_without_change_detected")),"pred_promise_without_change":bool(row.get("promise_without_change_detected")),"expected_response_without_evidence":bool(case.get("response_without_evidence_detected")),"pred_response_without_evidence":bool(row.get("response_without_evidence_detected")),"expected_new_regression":bool(case.get("new_regression_expected")),"pred_new_regression":pred_reg,"latency_seconds":time.perf_counter()-t,"llm_calls":state.metrics.get("llm_calls",0),"run_status":state.status,"hard_invariant_failure_count":len(state.hard_invariant_failures)})
    rep=_repeatability(initial_rows,repeats)
    hard_run_failures=sum(int(r.get("hard_invariant_failure_count",0)>0 or r.get("run_status")=="failed_validation") for r in initial_rows+revision_rows+rebuttal_rows)
    return {"gold_hidden_from_review_pipeline":True,"hard_integrity_run_failures":hard_run_failures,"independent_evaluator_enabled":evaluator is not None,"evaluator_models":({"judge_model_a":getattr(evaluator,"judge_model_a",None),"judge_model_b":getattr(evaluator,"judge_model_b",None),"adjudicator_model":getattr(evaluator,"adjudicator_model",None)} if evaluator is not None else {}),"lexical_similarity_used_for_detection":False,"case_count":len(scientific)+len(domain)+len(severity_cases)+len(revision)+len(rebuttal),"model_run_count":len(initial_rows)+len(revision_rows)+len(rebuttal_rows)+(2*len(counterfactual_rows)),"initial_review":{"metrics":aggregate(initial_rows),"repeatability":rep,"cases":initial_rows},"revision":{"accuracy":round(sum(r["correct"] for r in revision_rows)/max(1,len(revision_rows)),4),"cases":revision_rows},"rebuttal":{"metrics":_rebuttal_metrics(rebuttal_rows),"cases":rebuttal_rows},"counterfactual":{"metrics":_counterfactual_metrics(counterfactual_rows),"cases":counterfactual_rows}}
