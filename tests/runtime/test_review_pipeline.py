from __future__ import annotations
import asyncio
from pathlib import Path

from referee.config import ReviewConfig
from referee.engine import ReviewEngine
from referee.providers.scripted import ScriptedLLMProvider, ScriptedSearchProvider
from referee.stages import CORE_INITIAL_STAGES


def _core():
    return {
        "review_protocol": "beihang-referee",
        "classification": {"field":"test","domain":"test","design":"observational","inference_type":"causal","study_type":"empirical"},
        "manuscript_summary": {"research_question":"Does X improve Y?","approach":"observational","main_results":"20% improvement claimed","claimed_contribution":"causal improvement claim","developmental_stage":"empirical manuscript"},
        "claims": [{
            "claim_id":"C001","text":"Treatment X improves outcome Y by 20%.","claim_type":"causal","centrality":"central","scope":"main result",
            "proof_burden":["causal identification"],"evidence_anchor_ids":["A001"],"support_status":"weak","confidence":"moderate","alternatives":[]
        }],
        "evidence_anchors": [{
            "anchor_id":"A001","source_type":"manuscript","document_id":"D1","locator":"body",
            "quote_or_fact":"We claim treatment X improves outcome Y by 20%.","supports":"C001","confidence":"high",
            "url":None,"content_status":None,"content_sha256":None
        }],
        "candidate_concerns": [{
            "concern_id":"MC001","title":"Causal identification is not established","severity":"major","claim_ids":["C001"],"evidence_anchor_ids":["A001"],
            "failure_mechanism":"The manuscript states a causal improvement claim but the supplied design description does not establish an intervention or identification strategy separating treatment from confounding.",
            "scientific_consequence":"The 20% result cannot be interpreted as a causal treatment effect on the evidence supplied.",
            "minimum_resolution":"Reframe the conclusion as associational unless a valid identification strategy is documented and justified.",
            "closure_criterion":"Remove causal language or provide and validate the identification strategy supporting a causal interpretation.",
            "reviewer_confidence":0.9,"external_verification_required":False,"uncertainties":[],"suggested_validation_checks":[]
        }],
        "minor_concerns":[],"strengths":[],"observations":[],"literature_queries":[],"specialist_requests":[],
        "overall_scientific_confidence":0.45,"remaining_uncertainties":[]
    }


def _verdict():
    return {
        "status":"verified","severity":"major","steelman":"The authors may intend the word improves descriptively rather than causally.",
        "steelman_survives":True,"steelman_survival_reason":"The registered central claim is explicitly causal, so the interpretation remains consequential.",
        "rationale":"The frozen claim and anchor support the concern and the requested correction is proportionate.","confidence":0.92,
        "entailment": {
            "claim_mapping_valid":True,"anchors_support_failure_mechanism":True,"scientific_consequence_proportionate":True,
            "minimum_resolution_sufficient":True,"closure_criterion_testable":True,"steelman_survival_supported":True,
            "manuscript_contradiction_found":False
        },
        "uncertainties":[]
    }


def _empty_specialist():
    return {"candidate_concerns": [], "evidence_anchors": [], "notes": [], "uncertainties": []}


def test_core_pipeline_has_seven_default_stages():
    assert len(CORE_INITIAL_STAGES) == 7
    assert [s.stage_id for s in CORE_INITIAL_STAGES] == [
        "C01_ingest","C02_core_review","C03_targeted_evidence","C04_targeted_specialists",
        "C05_hard_evidence_gate","C06_independent_verify","C07_finalize"
    ]


def test_core_pipeline_smoke(tmp_path):
    paper=tmp_path/'paper.md'
    paper.write_text('# Paper\nWe claim treatment X improves outcome Y by 20%.',encoding='utf-8')
    responses={
        'core_review':_core(),
        'core_specialist:statistics_causal':_empty_specialist(),
        'core_specialist:methods':_empty_specialist(),
        'core_verify:MC-CORE-REVIEWER-0001':_verdict(),
    }
    cfg=ReviewConfig(mode='deep',pipeline='core',run_root=str(tmp_path/'runs'),enable_literature_search=False)
    llm=ScriptedLLMProvider(responses)
    engine=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id='core-smoke'))
    assert state.metrics['pipeline']=='core'
    assert len(state.stage_records)==7
    assert len(state.admitted_concerns)==1
    assert state.admitted_concerns[0]['steelman'].startswith('The authors may')
    assert state.final_review_exportable is True
    assert not state.hard_invariant_failures
    verify_call=next(c for c in llm.calls if c.operation.startswith('core_verify:'))
    assert '_generator' not in verify_call.user
    assert '_source_agent' not in verify_call.user
    assert '_task_id' not in verify_call.user
    assert 'ADDITIONAL MANUSCRIPT CONTRADICTION CONTEXT' in verify_call.user


def test_core_novelty_concern_fails_closed_without_external_evidence(tmp_path):
    paper=tmp_path/'novelty.md'
    paper.write_text('# Paper\nWe introduce the first framework for X.',encoding='utf-8')
    core=_core()
    core['classification']={"field":"test","domain":"test","design":"conceptual","inference_type":"descriptive","study_type":"theoretical"}
    core['claims'][0].update({"text":"This is the first framework for X.","claim_type":"novelty","centrality":"central"})
    core['evidence_anchors'][0]['quote_or_fact']='We introduce the first framework for X.'
    core['candidate_concerns'][0].update({
        "title":"Novelty is not established against prior art",
        "failure_mechanism":"Existing work may already establish the claimed novelty.",
        "scientific_consequence":"The central novelty claim may not be supportable.",
        "minimum_resolution":"Ground the novelty claim in verified prior art or narrow it.",
        "closure_criterion":"Provide verified prior-art evidence supporting the narrowed novelty claim.",
        "external_verification_required":False,
    })
    core['specialist_requests']=[{"task_id":"T001","specialist":"literature","claim_ids":["C001"],"objective":"audit novelty","priority":"high","evidence_needs":[]}]
    responses={
        'core_review':core,
        'core_specialist:literature':_empty_specialist(),
    }
    cfg=ReviewConfig(mode='standard',pipeline='core',run_root=str(tmp_path/'runs'),enable_literature_search=False)
    engine=ReviewEngine(llm=ScriptedLLMProvider(responses),search=ScriptedSearchProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id='core-novelty'))
    assert not state.admitted_concerns
    errors=' '.join(str(x.get('admission_errors') or []) for x in state.rejected_concerns)
    assert 'novelty/prior-art' in errors


def test_core_duplicate_major_concerns_are_collapsed(tmp_path):
    paper=tmp_path/'dup.md'
    paper.write_text('# Paper\nWe claim treatment X improves outcome Y by 20%.',encoding='utf-8')
    core=_core()
    second=dict(core['candidate_concerns'][0])
    second.update({
        'concern_id':'MC002',
        'title':'Causal effect is not identified',
        'failure_mechanism':'The causal treatment-effect claim lacks an identification strategy separating treatment from confounding.',
        'reviewer_confidence':0.8,
    })
    core['candidate_concerns'].append(second)
    responses={
        'core_review':core,
        'core_specialist:statistics_causal':_empty_specialist(),
        'core_specialist:methods':_empty_specialist(),
        'core_verify:MC-CORE-REVIEWER-0001':_verdict(),
    }
    cfg=ReviewConfig(mode='deep',pipeline='core',run_root=str(tmp_path/'runs'),enable_literature_search=False)
    engine=ReviewEngine(llm=ScriptedLLMProvider(responses),search=ScriptedSearchProvider(),config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(engine.review([str(paper)],run_id='core-dup'))
    assert len(state.admitted_concerns)==1
    assert any('near-duplicate concern' in ' '.join(x.get('admission_errors') or []) for x in state.rejected_concerns)
