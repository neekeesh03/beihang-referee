from __future__ import annotations

import asyncio
import csv
import html
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .._resources import resource_root
from ..config import ReviewConfig
from ..engine import ReviewEngine
from ..providers.openai_compatible import OpenAICompatibleProvider
from ..providers.scholarly_search import FederatedScholarlySearchProvider
from ..stages import stages_for_mode
from ..evals.corpus import load_corpus, all_case_count
from ..evals.full_suite import run_full_suite
from ..evals.end_to_end import run_end_to_end_cases
from ..evals.judge import ScientificDefectEvaluator
from ..evals.ablations import ABLATIONS, build_ablation_stages
from .adversarial import run_adversarial_integrity_suite
from .behavioral import run_model_backed_behavioral_suite
from .release import verify_release_manifest, build_experiment_manifest, sha_file

PRIMARY_METRIC_PATHS = {
    "major_concern_precision": ("initial_review","metrics","major_concern_precision"),
    "scientific_defect_recall": ("initial_review","metrics","scientific_defect_recall"),
    "ccore_control_false_positive_rate": ("initial_review","metrics","ccore_control_false_positive_rate"),
    "mechanism_accuracy": ("initial_review","metrics","mechanism_accuracy"),
    "counterfactual_sensitivity_pass_rate": ("counterfactual","metrics","causal_sensitivity_pass_rate"),
    "anchor_integrity_rate": ("initial_review","metrics","anchor_integrity_rate"),
    "citation_support_accuracy": ("initial_review","metrics","citation_support_accuracy"),
}

def _deep_get(obj:dict[str,Any], path:tuple[str,...]):
    cur:Any=obj
    for p in path:
        if not isinstance(cur,dict): return None
        cur=cur.get(p)
    return cur

def _write_json(path:Path,obj:Any):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")

def _write_jsonl(path:Path,rows:list[dict[str,Any]]):
    path.write_text("".join(json.dumps(r,ensure_ascii=False,default=str)+"\n" for r in rows),encoding="utf-8")

def _write_csv(path:Path, rows:list[dict[str,Any]], fields:list[str]|None=None):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=fields or sorted({k for r in rows for k in r.keys() if not isinstance(r.get(k),(dict,list))})
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:r.get(k) for k in fields})

def _success_criteria() -> dict[str,Any]:
    root=resource_root(); p=root/"validation"/"SUCCESS_CRITERIA.json"
    return json.loads(p.read_text(encoding="utf-8"))

def _criterion_pass(value:Any, spec:dict[str,Any]) -> bool|None:
    if not isinstance(value,(int,float)): return None
    t=float(spec["threshold"]); d=spec["direction"]
    return value>=t if d==">=" else value<=t if d=="<=" else None

def _criteria_evaluation(result:dict[str,Any], adversarial:dict[str,Any], behavioral:dict[str,Any]|None=None) -> dict[str,Any]:
    criteria=_success_criteria(); rows=[]
    for name,spec in criteria["primary_metrics"].items():
        value=_deep_get(result,PRIMARY_METRIC_PATHS[name]); rows.append({"metric":name,"value":value,"direction":spec["direction"],"threshold":spec["threshold"],"passed":_criterion_pass(value,spec)})
    deterministic=adversarial.get("deterministic_integrity_pass_rate") == 1.0 and adversarial.get("contract_test_pass_rate") == 1.0 and adversarial.get("all_critical_pass") is True
    behavioral_ok=(behavioral or {}).get("all_pass") if behavioral is not None else None
    return {"predeclared":criteria,"primary":rows,"deterministic_integrity_passed":deterministic,"model_backed_behavioral_passed":behavioral_ok,"all_primary_available":all(r["passed"] is not None for r in rows),"all_primary_passed":all(r["passed"] is True for r in rows) if all(r["passed"] is not None for r in rows) else None}

def _static_source_checks(*, run_pytest: bool=True) -> dict[str,Any]:
    root=Path(__file__).resolve().parents[2]
    checks={"python_compile":True,"pytest":None if run_pytest else "skipped_by_explicit_option","pytest_output":"","structured_gold_defect_cases":0,"benchmark_cases":all_case_count()}
    try:
        subprocess.run([sys.executable,"-m","compileall","-q",str(root/"referee")],check=True,capture_output=True,text=True)
    except Exception as exc:
        checks["python_compile"]=False;checks["compile_error"]=str(exc)
    gold=resource_root()/"benchmark_corpus"/"structured_gold.jsonl"
    if gold.exists(): checks["structured_gold_defect_cases"]=sum(1 for line in gold.read_text(encoding="utf-8").splitlines() if line.strip())
    tests=root/"tests"
    if run_pytest and tests.is_dir():
        p=subprocess.run([sys.executable,"-m","pytest","-q"],cwd=root,capture_output=True,text=True)
        checks["pytest"]=p.returncode==0;checks["pytest_output"]=(p.stdout+p.stderr)[-12000:]
    return checks

def _make_evaluator(llm, *,judge_model_a:str,judge_model_b:str,adjudicator_model:str) -> ScientificDefectEvaluator:
    core=resource_root()/"core"
    return ScientificDefectEvaluator(llm=llm,judge_model_a=judge_model_a,judge_model_b=judge_model_b,adjudicator_model=adjudicator_model,judge_prompt=(core/"BENCHMARK_JUDGE_PROMPT.md").read_text(encoding="utf-8"),adjudicator_prompt=(core/"BENCHMARK_ADJUDICATOR_PROMPT.md").read_text(encoding="utf-8"))

def _engine_builder(llm, search, *,review_model:str,verifier_model:str,run_root:Path, ablation:str="full_system"):
    def factory(mode:str, root:Path):
        cfg=ReviewConfig(mode="exhaustive",pipeline="full",review_mode=mode,run_root=str(root),model=review_model,verifier_model=verifier_model,enable_journal_calibration=False)
        stages=stages_for_mode(mode, pipeline="full")
        if mode=="initial" and ablation!="full_system":
            stages,spec=build_ablation_stages(ablation,stages)
            for k,v in spec.config_overrides.items(): setattr(cfg,k,v)
        return ReviewEngine(llm=llm,search=search,config=cfg,stages=stages)
    return factory

def _initial_engine_factory(llm,search,*,review_model:str,verifier_model:str,ablation:str):
    def factory(run_root:Path):
        cfg=ReviewConfig(mode="exhaustive",pipeline="full",review_mode="initial",run_root=str(run_root),model=review_model,verifier_model=verifier_model,enable_journal_calibration=False)
        stages,spec=build_ablation_stages(ablation,stages_for_mode("initial", pipeline="full"))
        for k,v in spec.config_overrides.items(): setattr(cfg,k,v)
        return ReviewEngine(llm=llm,search=search,config=cfg,stages=stages)
    return factory

def _flatten_case_rows(result:dict[str,Any]) -> list[dict[str,Any]]:
    rows=[]
    for r in result.get("initial_review",{}).get("cases",[]): rows.append({"benchmark":"initial",**r})
    for r in result.get("revision",{}).get("cases",[]): rows.append({"benchmark":"revision",**r})
    for r in result.get("rebuttal",{}).get("cases",[]): rows.append({"benchmark":"rebuttal",**r})
    for r in result.get("counterfactual",{}).get("cases",[]): rows.append({"benchmark":"counterfactual",**r})
    return rows

def _failed_case_rows(rows:list[dict[str,Any]]) -> list[dict[str,Any]]:
    failed=[]
    for r in rows:
        b=r.get("benchmark")
        bad=(b=="initial" and not bool(r.get("correct"))) or (b in {"revision","rebuttal"} and not bool(r.get("correct"))) or (b=="counterfactual" and not bool(r.get("causal_sensitivity_pass")))
        if bad: failed.append(r)
    return failed

def _metrics_rows(result:dict[str,Any]) -> list[dict[str,Any]]:
    m=result.get("initial_review",{}).get("metrics",{}); rows=[]
    for k,v in m.items():
        if not isinstance(v,(dict,list)): rows.append({"section":"initial_review","metric":k,"value":v})
    for section in ("revision","rebuttal","counterfactual"):
        sub=result.get(section,{})
        metrics=sub.get("metrics",{}) if isinstance(sub,dict) else {}
        if section=="revision" and "accuracy" in sub: metrics={"accuracy":sub["accuracy"],**metrics}
        for k,v in metrics.items():
            if not isinstance(v,(dict,list)): rows.append({"section":section,"metric":k,"value":v})
    return rows

def _domain_rows(result:dict[str,Any]) -> list[dict[str,Any]]:
    per=result.get("initial_review",{}).get("metrics",{}).get("per_domain",{})
    return [{"domain":k,**v} for k,v in per.items()]

def _repeatability_rows(result:dict[str,Any]) -> list[dict[str,Any]]:
    rep=result.get("initial_review",{}).get("repeatability",{})
    return [{"metric":k,"value":v} for k,v in rep.items() if not isinstance(v,(dict,list))]

def _citation_rows(result:dict[str,Any]) -> list[dict[str,Any]]:
    m=result.get("initial_review",{}).get("metrics",{})
    keys=["citation_existence_accuracy","citation_metadata_accuracy","citation_support_accuracy","fabricated_reference_rate","metadata_mismatch_rate","unsupported_citation_rate","contradicted_citation_rate","unverifiable_citation_rate"]
    return [{"metric":k,"value":m.get(k)} for k in keys]

def _html_report(summary:dict[str,Any]) -> str:
    rows=summary.get("success_criteria",{}).get("primary",[])
    trs="".join(f"<tr><td>{html.escape(str(r['metric']))}</td><td>{html.escape(str(r['value']))}</td><td>{html.escape(str(r['direction']))} {r['threshold']}</td><td>{html.escape(str(r['passed']))}</td></tr>" for r in rows)
    return "<!doctype html><meta charset='utf-8'><title>Referee validation</title><h1>Referee validation</h1><p>Results are tied to the immutable run manifest. No aggregate opaque score is used.</p><table border='1'><tr><th>Metric</th><th>Value</th><th>Predeclared criterion</th><th>Pass</th></tr>"+trs+"</table>"

async def run_validation_campaign(*, suite:str, output_dir:str|Path, review_model:str|None=None, verifier_model:str|None=None, judge_model_a:str|None=None, judge_model_b:str|None=None, adjudicator_model:str|None=None, search_backend:str="federated", scholarly_providers:list[str]|None=None, repeats:int=3, limit_per_corpus:int|None=None, skip_source_tests:bool=False, require_external_independence:bool=False) -> dict[str,Any]:
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    release=verify_release_manifest(); static=_static_source_checks(run_pytest=not skip_source_tests)
    adversarial=run_adversarial_integrity_suite(resource_root())
    integrity={"release_manifest":release,"static":static,"adversarial":adversarial}
    _write_json(out/"integrity_results.json",integrity)
    if not release.get("valid") or not adversarial.get("all_critical_pass") or static.get("python_compile") is False or static.get("pytest") is False:
        summary={"status":"failed_validation","suite":suite,"integrity":integrity,"final_review_exportable":False}
        _write_json(out/"validation_summary.json",summary);return summary
    if suite=="integrity":
        summary={"status":"completed","suite":"integrity","integrity":integrity,"scientific_performance_not_evaluated":True}
        _write_json(out/"validation_summary.json",summary);return summary
    if not review_model:
        raise ValueError("Full validation requires an explicit review model; pass --model or set REFEREE_MODEL")
    verifier_model=verifier_model or review_model;judge_model_a=judge_model_a or review_model;judge_model_b=judge_model_b or verifier_model;adjudicator_model=adjudicator_model or judge_model_b
    providers=scholarly_providers or ["crossref","openalex","semantic_scholar","pubmed","arxiv","europe_pmc"]
    llm=OpenAICompatibleProvider(default_model=review_model)
    search=FederatedScholarlySearchProvider(providers,max_concurrency=8) if search_backend=="federated" else None
    evaluator=_make_evaluator(llm,judge_model_a=judge_model_a,judge_model_b=judge_model_b,adjudicator_model=adjudicator_model)
    experiment=build_experiment_manifest(release_verification=release,review_model=review_model,verifier_model=verifier_model,judge_model_a=judge_model_a,judge_model_b=judge_model_b,adjudicator_model=adjudicator_model,search_backend=search_backend,scholarly_providers=providers,repeats=repeats,ablation_names=[x.name for x in ABLATIONS])
    experiment["created_at"]=datetime.now(timezone.utc).isoformat();experiment["limit_per_corpus"]=limit_per_corpus
    experiment["external_independence_required"]=bool(require_external_independence)
    experiment["scientific_pipeline_under_model_backed_ablation_validation"]="full"
    experiment["core_pipeline_model_backed_validation_status"]="not_measured_by_this_full_ablation_campaign"
    if require_external_independence and not (experiment.get("evaluation_independence") or {}).get("external_independent_validation"):
        summary={"status":"failed_validation","suite":"full","reason":"external_evaluator_independence_requirement_not_met","evaluation_independence":experiment.get("evaluation_independence"),"final_results_trustworthy":False}
        _write_json(out/"run_manifest.json",experiment);_write_json(out/"validation_summary.json",summary);return summary
    _write_json(out/"run_manifest.json",experiment)  # frozen before first model call
    started=time.perf_counter()
    factory=_engine_builder(llm,search,review_model=review_model,verifier_model=verifier_model,run_root=out/"runs")
    if limit_per_corpus == 0:
        behavioral={"status":"orchestration_smoke_skipped","total":0,"passed":0,"model_backed_adversarial_pass_rate":None,"all_pass":True,"cases":[],"tautological_checks":0}
    else:
        behavioral=await run_model_backed_behavioral_suite(factory,llm,judge_model_a)
    _write_json(out/"behavioral_adversarial_results.json",behavioral)
    if not behavioral.get("all_pass"):
        summary={"status":"failed_validation","suite":"full","validation_release":experiment["validation_release"],"experimental_configuration_id":experiment["experimental_configuration_id"],"evaluation_independence":experiment.get("evaluation_independence"),"reason":"model_backed_behavioral_adversarial_failure","behavioral_adversarial":behavioral,"final_results_trustworthy":False}
        _write_json(out/"validation_summary.json",summary);return summary
    result=await run_full_suite(factory,root=None,limit_per_corpus=limit_per_corpus,repeats=repeats,run_counterfactuals=True,evaluator=evaluator)
    cases=_flatten_case_rows(result);_write_jsonl(out/"per_case_results.jsonl",cases);_write_jsonl(out/"failed_cases.jsonl",_failed_case_rows(cases))
    _write_csv(out/"metrics.csv",_metrics_rows(result),["section","metric","value"]);_write_csv(out/"domain_metrics.csv",_domain_rows(result));_write_csv(out/"repeatability_metrics.csv",_repeatability_rows(result),["metric","value"]);_write_csv(out/"citation_metrics.csv",_citation_rows(result),["metric","value"])
    # Causal architecture ablations on the same hidden-gold initial/domain cases.
    initial_cases=load_corpus("scientific")+load_corpus("domain")
    if limit_per_corpus is not None: initial_cases=load_corpus("scientific")[:limit_per_corpus]+load_corpus("domain")[:limit_per_corpus]
    ablation_rows=[]
    for spec in ABLATIONS:
        af=_initial_engine_factory(llm,search,review_model=review_model,verifier_model=verifier_model,ablation=spec.name)
        ar=await run_end_to_end_cases(initial_cases,af,evaluator=evaluator)
        m=ar["metrics"]
        ablation_rows.append({"configuration":spec.name,"major_concern_precision":m.get("major_concern_precision"),"scientific_defect_recall":m.get("scientific_defect_recall"),"ccore_control_false_positive_rate":m.get("ccore_control_false_positive_rate"),"mechanism_accuracy":m.get("mechanism_accuracy"),"severity_macro_f1":m.get("severity_macro_f1"),"citation_support_accuracy":m.get("citation_support_accuracy"),"mean_cost_llm_calls":m.get("mean_cost_llm_calls"),"mean_latency_seconds":m.get("mean_latency_seconds")})
    _write_csv(out/"ablation_metrics.csv",ablation_rows)
    success=_criteria_evaluation(result,adversarial,behavioral)
    hard_run_failures=int(result.get("hard_integrity_run_failures") or 0)
    summary={"status":"failed_validation" if hard_run_failures else "completed","suite":"full","validation_release":experiment["validation_release"],"experimental_configuration_id":experiment["experimental_configuration_id"],"elapsed_seconds":round(time.perf_counter()-started,3),"case_count":result.get("case_count"),"model_run_count":result.get("model_run_count"),"hard_integrity_run_failures":hard_run_failures,"final_results_trustworthy":hard_run_failures==0,"gold_hidden_from_review_pipeline":True,"lexical_similarity_used_for_detection":False,"success_criteria":success,"metrics":result.get("initial_review",{}).get("metrics",{}),"revision_accuracy":result.get("revision",{}).get("accuracy"),"rebuttal_metrics":result.get("rebuttal",{}).get("metrics",{}),"counterfactual_metrics":result.get("counterfactual",{}).get("metrics",{}),"repeatability":result.get("initial_review",{}).get("repeatability",{}),"adversarial_integrity":adversarial,"behavioral_adversarial":behavioral,"evaluation_independence":experiment.get("evaluation_independence"),"validation_claim_label":(experiment.get("evaluation_independence") or {}).get("label"),"scientific_pipeline_under_model_backed_ablation_validation":"full","core_pipeline_model_backed_validation_status":"not_measured_by_this_full_ablation_campaign"}
    _write_json(out/"validation_summary.json",summary);(out/"validation_report.html").write_text(_html_report(summary),encoding="utf-8")
    # Keep run_manifest.json immutable after the first model call. Results get a
    # separate hash manifest so post-result bookkeeping cannot rewrite the
    # experimental configuration that generated them.
    result_files=["validation_summary.json","per_case_results.jsonl","metrics.csv","domain_metrics.csv","ablation_metrics.csv","repeatability_metrics.csv","citation_metrics.csv","failed_cases.jsonl","integrity_results.json","behavioral_adversarial_results.json","validation_report.html"]
    _write_json(out/"results_manifest.json",{"experimental_configuration_id":experiment["experimental_configuration_id"],"finished_at":datetime.now(timezone.utc).isoformat(),"results":{name:sha_file(out/name) for name in result_files}})
    return summary
