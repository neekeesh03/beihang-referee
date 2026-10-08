from __future__ import annotations
import asyncio
from pathlib import Path

from referee.config import ReviewConfig
from referee.engine import ReviewEngine
from referee.providers.scripted import ScriptedLLMProvider, ScriptedSearchProvider


def _core():
    return {
        "review_protocol":"beihang-referee",
        "classification":{"field":"test","domain":"test","design":"conceptual","inference_type":"descriptive","study_type":"theoretical"},
        "manuscript_summary":{"research_question":"What is X?","approach":"conceptual analysis","main_results":"A bounded framework is proposed.","claimed_contribution":"A clarified conceptual framework.","developmental_stage":"conceptual manuscript"},
        "claims":[{"claim_id":"C001","text":"The framework clarifies X.","claim_type":"descriptive","centrality":"central","scope":"main","proof_burden":["conceptual coherence"],"evidence_anchor_ids":["A001"],"support_status":"supported","confidence":"moderate","alternatives":[]}],
        "evidence_anchors":[{"anchor_id":"A001","source_type":"manuscript","document_id":"D1","locator":"body","quote_or_fact":"The framework clarifies X.","supports":"C001","confidence":"high","url":None,"content_status":None,"content_sha256":None}],
        "candidate_concerns":[],"minor_concerns":[],"strengths":["The main claim is clearly scoped."],"observations":[],
        "literature_queries":[],"specialist_requests":[],"overall_scientific_confidence":0.8,"remaining_uncertainties":[]
    }


def _empty_specialist():
    return {"candidate_concerns":[],"evidence_anchors":[],"notes":["No material specialist barrier identified."],"uncertainties":[]}


def test_scorecard_receives_evidence_bundle_and_reference_benchmark_cannot_promote_submission(tmp_path):
    paper=tmp_path/"paper.md"; paper.write_text("# Paper\nThe framework clarifies X.",encoding="utf-8")
    score={
        "scientific_gates":{},
        "dimensions":[{
            "dimension":"Overall scientific credibility / claim readiness","score":"8",
            "justification":"The frozen evidence supports the bounded central claim.",
            "evidence_basis":["claims:C001","evidence_anchors:A001"],"confidence":0.8
        }],
        "calibration_note":"Diagnostic only.",
        "measurement_status":"diagnostic_ordinal_uncalibrated",
        "precision_warning":"One-point differences are not precise measurements."
    }
    responses={"core_review":_core(),"core_specialist:theory":_empty_specialist(),"core_scorecard":score}
    cfg=ReviewConfig(mode="standard",pipeline="core",run_root=str(tmp_path/"runs"),enable_literature_search=False,
                     enable_scorecard=True,benchmark_profile="nature-published")
    llm=ScriptedLLMProvider(responses)
    engine=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id="score-bench"))
    call=next(c for c in llm.calls if c.operation=="core_scorecard")
    assert "DIMENSION EVIDENCE BUNDLE" in call.user
    assert "manuscript_digest" in call.user
    assert state.final_review["benchmark_comparison"]["decision_support_enabled"] is False
    assert state.final_review["submission_state"]["status"] != "SUBMISSION_TERRITORY"


def test_target_journal_without_profile_is_provisional_and_confidence_capped(tmp_path):
    paper=tmp_path/"paper.md"; paper.write_text("# Paper\nThe framework clarifies X.",encoding="utf-8")
    cal={
        "target_journal":"Nature","fit_score":8.5,"impact_potential_score":8.0,"publication_readiness_score":7.5,
        "audience_fit":"Potentially broad.","contribution_threshold":"Potentially relevant.","major_mismatch":None,
        "evidence_status":"provisional_model_prior","profile_source_count":0,
        "evidence_basis":["Frozen manuscript state only."],"confidence":0.9
    }
    responses={"core_review":_core(),"core_specialist:theory":_empty_specialist(),"core_target_journal_calibration":cal}
    cfg=ReviewConfig(mode="standard",pipeline="core",run_root=str(tmp_path/"runs"),enable_literature_search=False,
                     target_journal="Nature",enable_scorecard=False)
    llm=ScriptedLLMProvider(responses)
    engine=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id="journal-provisional"))
    out=state.final_review["target_journal_calibration"]
    assert out["evidence_status"]=="provisional_model_prior"
    assert out["profile_source_count"]==0
    assert out["confidence"]<=0.5
    assert "provisional" in " ".join(out["evidence_basis"]).lower()
