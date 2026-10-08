from __future__ import annotations
from collections import defaultdict
from typing import Any


def _structured_from_full(gold:dict[str,Any],category:str|None):
    from .gold import CONCEPTS
    if gold.get("required_mechanism_concepts"):return gold
    if category not in CONCEPTS:return None
    return {"defect_id":str(category).upper(),"category":category,"severity":gold.get("severity","major"),"required_mechanism_concepts":[{"concept":g[0],"acceptable_phrases":g} for g in CONCEPTS[category]],"scientific_consequence":[gold.get("scientific_consequence","")],"acceptable_resolutions":[gold.get("minimum_resolution",gold.get("closure_criterion",""))],"forbidden_misdiagnoses":[]}


def match_gold(gold:dict[str,Any],category:str|None,concerns:list[dict[str,Any]])->tuple[dict[str,Any]|None,float]:
    """Mechanism-based compatibility helper; never lexical/category weighted.

    Retained for external callers, but successful matching requires the hidden
    structured mechanism contract and two deterministic scientific judges.
    """
    from .judge import deterministic_judge_a,deterministic_judge_b,deterministic_adjudicate
    sg=_structured_from_full(gold,category)
    if not sg:return None,0.0
    best=None;score=0.0
    for c in concerns:
        a=deterministic_judge_a(sg,c);b=deterministic_judge_b(sg,c);f=deterministic_adjudicate(sg,c,a,b)
        s=float(f.get("confidence") or 0) if f.get("mechanism_match")=="yes" else 0.0
        if s>score:best,score=c,s
    return best,round(score,4)


def expected_calibration_error(rows:list[dict[str,Any]],bins:int=10)->float|None:
    pairs=[]
    for r in rows:
        conf=r.get("confidence")
        if isinstance(conf,(int,float)) and not isinstance(conf,bool) and "correct" in r:pairs.append((max(0,min(1,float(conf))),1.0 if r["correct"] else 0.0))
    if not pairs:return None
    ece=0.0
    for b in range(bins):
        lo,hi=b/bins,(b+1)/bins;bucket=[x for x in pairs if lo<=x[0]<(hi if b<bins-1 else hi+1e-9)]
        if bucket:
            cf=sum(x[0] for x in bucket)/len(bucket);ac=sum(x[1] for x in bucket)/len(bucket);ece+=len(bucket)/len(pairs)*abs(cf-ac)
    return round(ece,4)


def severity_macro_f1(rows:list[dict[str,Any]])->float:
    labels=sorted(set(r.get("gold_severity") for r in rows if r.get("gold_severity") not in {None,"none","security"}))
    f=[]
    for label in labels:
        tp=sum(r.get("gold_severity")==label and r.get("pred_severity")==label for r in rows);fp=sum(r.get("gold_severity")!=label and r.get("pred_severity")==label for r in rows);fn=sum(r.get("gold_severity")==label and r.get("pred_severity")!=label for r in rows)
        p=tp/max(1,tp+fp);rec=tp/max(1,tp+fn);f.append(2*p*rec/max(1e-12,p+rec))
    return round(sum(f)/len(f),4) if f else 0.0


def _mean(rows,key):
    vals=[float(r[key]) for r in rows if r.get(key) is not None]
    return round(sum(vals)/len(vals),4) if vals else None


def _citation_aggregate(rows:list[dict[str,Any]])->dict[str,Any]:
    keys=("citation_existence_accuracy","citation_metadata_accuracy","citation_support_accuracy","fabricated_reference_rate","metadata_mismatch_rate","unsupported_citation_rate","contradicted_citation_rate","unverifiable_citation_rate")
    return {k:_mean([{"v":r.get("citation_metrics",{}).get(k)} for r in rows if isinstance(r.get("citation_metrics"),dict)],"v") for k in keys}


def aggregate(rows:list[dict[str,Any]])->dict[str,Any]:
    positives=[r for r in rows if r.get("has_gold_defect",True)];negatives=[r for r in rows if not r.get("has_gold_defect",True)]
    detected=sum(bool(r.get("detected")) for r in positives);predicted=sum(int(r.get("predicted_major_count",0)) for r in rows)
    # Precision is scientific correctness, not target-gold matching. Unmatched
    # concerns are independently adjudicated; uncertain concerns are reported
    # as coverage gaps rather than silently counted false.
    valid_major=sum(int(r.get("validated_major_count", 1 if r.get("detected") else 0)) for r in rows)
    false_major=sum(int(r.get("invalid_major_count",r.get("false_major_count",0))) for r in rows)
    uncertain_major=sum(int(r.get("uncertain_major_count",0)) for r in rows)
    precision_denom=valid_major+false_major
    precision=valid_major/max(1,precision_denom);recall=detected/max(1,len(positives));ccore_fp=sum(bool(r.get("ccore_case_false_positive")) for r in negatives)
    per_domain=defaultdict(lambda:{"n":0,"gold_defects":0,"detected":0,"false_positive_cases":0})
    for r in rows:
        d=r.get("domain") or r.get("category") or "unspecified";per_domain[d]["n"]+=1
        if r.get("has_gold_defect"):per_domain[d]["gold_defects"]+=1;per_domain[d]["detected"]+=int(bool(r.get("detected")))
        elif r.get("ccore_case_false_positive"):per_domain[d]["false_positive_cases"]+=1
    severity_labels={r.get("gold_severity") for r in rows if r.get("gold_severity") in {"major","minor","observation"}}
    severity_coverage=sorted(severity_labels)
    sev_f1=severity_macro_f1(rows) if severity_labels=={"major","minor","observation"} else None
    out={"cases":len(rows),"gold_defect_cases":len(positives),"ccore_control_cases":len(negatives),"scientific_defect_recall":round(recall,4),"defect_recall":round(recall,4),"major_concern_precision":round(precision,4),"major_concern_precision_adjudicated_count":precision_denom,"major_concern_precision_coverage":round(precision_denom/max(1,predicted),4),"uncertain_major_count":uncertain_major,"false_positive_major_count":false_major,"false_positive_rate":round(false_major/max(1,predicted),4),"ccore_control_false_positive_rate":round(ccore_fp/max(1,len(negatives)),4) if negatives else None,"ccore_case_false_positive_rate":round(ccore_fp/max(1,len(negatives)),4) if negatives else None,"severity_macro_f1":sev_f1,"severity_class_coverage":severity_coverage,"calibration_ece":expected_calibration_error(rows),"anchor_integrity_rate":_mean(rows,"anchor_validity"),"claim_id_validity_rate":_mean(rows,"claim_id_validity"),"evidence_entailment_pass_rate":_mean(rows,"evidence_entailment_pass_rate"),"mechanism_accuracy":_mean(positives,"mechanism_correctness"),"consequence_accuracy":_mean(positives,"consequence_correctness"),"closure_quality":_mean(positives,"closure_quality"),"mean_cost_llm_calls":round(sum(r.get("llm_calls",0) for r in rows)/max(1,len(rows)),2),"mean_search_calls":round(sum(r.get("search_calls",0) for r in rows)/max(1,len(rows)),2),"mean_latency_seconds":round(sum(r.get("latency_seconds",0) for r in rows)/max(1,len(rows)),3),"per_domain":{k:{**v,"recall":round(v["detected"]/max(1,v["gold_defects"]),4) if v["gold_defects"] else None} for k,v in sorted(per_domain.items())}}
    out.update(_citation_aggregate(rows));out["hallucinated_citation_rate"]=out.get("fabricated_reference_rate")
    # Backward-compatible explicit mean names; the canonical public metric names
    # above remain mechanism_accuracy/consequence_accuracy/closure_quality.
    out["mean_mechanism_correctness"]=out.get("mechanism_accuracy")
    out["mean_consequence_correctness"]=out.get("consequence_accuracy")
    out["mean_closure_quality"]=out.get("closure_quality")
    out["mean_evidence_entailment_pass_rate"]=out.get("evidence_entailment_pass_rate")
    return out
