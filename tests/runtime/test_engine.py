from pathlib import Path
import asyncio
from referee import ReviewConfig, ReviewEngine
from referee.providers import ScriptedLLMProvider, ScriptedSearchProvider


def _core_review():
    return {
        "review_protocol":"beihang-referee","review_mode":"initial",
        "manuscript_summary":{"research_question":"Does X improve Y?","approach":"Unspecified design","main_results":"20% improvement claimed","claimed_contribution":"Causal effect of X on Y"},
        "claim_registry":[{"claim_id":"C001","claim_text":"X improves Y","claim_type":"causal","importance":"central","location":"body","supporting_evidence":["A001"],"support_strength":"weak"}],
        "evidence_anchors":[{"anchor_id":"A001","source_type":"manuscript","section":"body","page_or_location":"body","source_identifier":None,"title":None,"year":None,"quote_or_fact":"treatment X improves outcome Y by 20%","verification_status":"requires_deterministic_validation"}],
        "strengths":[],"major_concerns":[],"minor_concerns":[],"observations":[],
        "novelty_assessment":{"status":"external_verification_required","assessment":"No verified external evidence supplied.","external_anchor_ids":[]},
        "reproducibility_assessment":{"status":"insufficient_information","assessment":"Not enough information.","missing_requirements":[]},
        "numerical_consistency":{"status":"not_assessable","issues":[]},
        "review_summary":{"central_claims_supported":[],"central_claims_at_risk":["C001"],"strongest_concern_ids":[],"overall_scientific_confidence":0.4,"remaining_uncertainties":[]},
    }


def _concern():
    return {
        "concern_id":"MC001", "title":"Unsupported causal interpretation", "severity":"major",
        "claim_ids":["C001"], "evidence_anchor_ids":["A001"],
        "failure_mechanism":"The design does not isolate the treatment effect.",
        "scientific_consequence":"The headline causal claim is not identified.",
        "minimum_resolution":"Reframe as associational or add a design that identifies the effect.",
        "closure_criterion":"The main claim is non-causal or a valid identification strategy is demonstrated.",
        "reviewer_confidence":0.93,
        "steelman":"The authors may intend improves as a descriptive association rather than a causal claim.",
        "steelman_survives":True,
        "steelman_survival_reason":"The manuscript still presents the statement as a treatment effect without an identification strategy.",
        "external_verification_required":False,
        "uncertainties":[],"suggested_validation_checks":[],
    }


def _verdict(status="verified"):
    return {
        "status":status,
        "rationale":"Frozen manuscript evidence supports the concern." if status=="verified" else "Insufficient support.",
        "entailment":{
            "claim_mapping_valid":True,"anchors_support_failure_mechanism":True,
            "scientific_consequence_proportionate":True,"minimum_resolution_sufficient":True,
            "closure_criterion_testable":True,"steelman_survival_supported":True,
            "manuscript_contradiction_found":False,
        },
        "uncertainties":[],
    }


def test_engine_end_to_end_scripted(tmp_path):
    paper = tmp_path / "paper.md"
    paper.write_text("# Paper\nWe claim treatment X improves outcome Y by 20%.", encoding="utf-8")
    concern = _concern()
    responses = {
        "classification": {"field":"test", "specialists":["methods_design"]},
        "core_peer_review": _core_review(),
        "review_plan": {"tasks":[{"task_id":"T001","specialist":"methods_design","claim_ids":["C001"],"objective":"audit causal claim","priority":"high","evidence_needs":[]}]},
        "numerical_ledger": {"items":[],"concerns":[],"evidence_anchors":[]},
        "literature_plan": {"queries":[]},
        "literature_synthesis": {"concerns":[],"evidence_anchors":[],"novelty":{},"pivotal_sources":[]},
        "specialist:methods_design": {"concerns":[concern],"evidence_anchors":[],"notes":[],"uncertainty":[]},
        "redteam_steelman": {"concerns":[concern],"evidence_anchors":[]},
        "entailment:MC001": {"status":"supported","rationale":"The cited claim and design limitation support the concern.","consequence_proportionate":True,"closure_testable":True},
        "concern_verifier:MC001": _verdict(),
        "reliability": {"status":"stable"},
        "final_synthesis": {"critical_gates":{"claim_support":{"status":"fail"}},
                            "final_review":{"decision_brief":{"no_material_scientific_barriers":False},"minor_comments":[],"strengths":[],"limitations":[]}},
        "journal_calibration": {"journals":[]},
    }
    cfg = ReviewConfig(mode="deep", pipeline="full", run_root=str(tmp_path / "runs"))
    engine = ReviewEngine(llm=ScriptedLLMProvider(responses), search=ScriptedSearchProvider(), config=cfg,
                          package_root=str(Path(__file__).resolve().parents[2]))
    state = asyncio.run(engine.review([str(paper)], query="test review", run_id="t1"))
    assert state.status == "completed"
    assert len(state.admitted_concerns) == 1
    rec=state.verification_records[0]
    assert rec["generator_context_id"] != rec["verifier_context_id"]
    assert rec["concern_sha256"] and rec["anchor_bundle_sha256"] and rec["claim_registry_sha256"] and rec["manuscript_sha256"]
    assert rec["deterministic_postcheck"]["model_status_trusted_as_proof"] is False
    assert state.admitted_concerns[0]["provenance_gate"]["status"] == "passed"
    assert (tmp_path / "runs" / "t1" / "artifacts" / "review.md").exists()


def test_model_written_verified_status_cannot_override_postchecks(tmp_path):
    paper = tmp_path / "paper.md"
    paper.write_text("# Paper\nWe claim treatment X improves outcome Y by 20%.", encoding="utf-8")
    concern = _concern()
    bad_verdict = _verdict()
    bad_verdict["entailment"]["anchors_support_failure_mechanism"] = False
    responses = {
        "classification":{"field":"test","specialists":["methods_design"]},
        "core_peer_review":_core_review(),
        "review_plan":{"tasks":[{"task_id":"T001","specialist":"methods_design","claim_ids":["C001"],"objective":"audit","priority":"high","evidence_needs":[]}]},
        "numerical_ledger":{"items":[],"concerns":[],"evidence_anchors":[]},
        "literature_plan":{"queries":[]},"literature_synthesis":{"concerns":[],"evidence_anchors":[],"novelty":{},"pivotal_sources":[]},
        "specialist:methods_design":{"concerns":[concern],"evidence_anchors":[],"notes":[],"uncertainty":[]},
        "redteam_steelman":{"concerns":[concern],"evidence_anchors":[]},
        "entailment:MC001":{"status":"supported","rationale":"supported","consequence_proportionate":True,"closure_testable":True},
        "concern_verifier:MC001":bad_verdict,
        "reliability":{"status":"stable"},
        "final_synthesis":{"critical_gates":{},"final_review":{"decision_brief":{},"minor_comments":[],"strengths":[],"limitations":[]}},
        "journal_calibration":{"journals":[]},
    }
    llm=ScriptedLLMProvider(responses)
    engine=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=ReviewConfig(mode="deep", pipeline="full", run_root=str(tmp_path/"runs")),package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id="postcheck"))
    assert state.admitted_concerns == []
    rec=state.verification_records[0]
    assert rec["judge_status"] == "verified"
    assert rec["verification_status"] == "rejected"
    assert any("anchors_support_failure_mechanism" in e for e in rec["deterministic_postcheck"]["errors"])


def test_verifier_is_blind_to_generator_and_provenance_metadata(tmp_path):
    paper = tmp_path / "paper.md"
    paper.write_text("# Paper\nWe claim treatment X improves outcome Y by 20%.", encoding="utf-8")
    concern=_concern()
    responses={
        "classification":{"field":"test","specialists":["methods_design"]},"core_peer_review":_core_review(),
        "review_plan":{"tasks":[{"task_id":"T001","specialist":"methods_design","claim_ids":["C001"],"objective":"audit","priority":"high","evidence_needs":[]}]},
        "numerical_ledger":{"items":[],"concerns":[],"evidence_anchors":[]},"literature_plan":{"queries":[]},
        "literature_synthesis":{"concerns":[],"evidence_anchors":[],"novelty":{},"pivotal_sources":[]},
        "specialist:methods_design":{"concerns":[concern],"evidence_anchors":[],"notes":[],"uncertainty":[]},
        "redteam_steelman":{"concerns":[concern],"evidence_anchors":[]},
        "entailment:MC001":{"status":"supported","rationale":"supported","consequence_proportionate":True,"closure_testable":True},
        "concern_verifier:MC001":_verdict(),"reliability":{"status":"stable"},
        "final_synthesis":{"critical_gates":{},"final_review":{"decision_brief":{},"minor_comments":[],"strengths":[],"limitations":[]}},"journal_calibration":{"journals":[]}}
    llm=ScriptedLLMProvider(responses)
    engine=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=ReviewConfig(mode="deep", pipeline="full", run_root=str(tmp_path/"runs")),package_root=str(Path(__file__).resolve().parents[2]))
    asyncio.run(engine.review([str(paper)],run_id="blind"))
    call=next(c for c in llm.calls if c.operation=="concern_verifier:MC001")
    assert "FROZEN_EVIDENCE_BUNDLE" in call.user and "PROPOSED_CONCERN" in call.user and "MANUSCRIPT" in call.user
    assert "_generator" not in call.user
    assert "_source_agent" not in call.user
    assert "provenance_gate" not in call.user
    assert "original reviewer's hidden reasoning" in call.system
