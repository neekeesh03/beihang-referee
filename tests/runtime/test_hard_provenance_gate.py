import asyncio
from pathlib import Path
from referee import ReviewConfig, ReviewEngine
from referee.providers import ScriptedLLMProvider, ScriptedSearchProvider


def _core():
    return {
      'review_protocol':'beihang-referee','review_mode':'initial',
      'manuscript_summary':{'research_question':'X?','approach':'test','main_results':'claim X','claimed_contribution':'claim X'},
      'claim_registry':[{'claim_id':'C001','claim_text':'claim X','claim_type':'causal','importance':'central','location':'body','supporting_evidence':['A001'],'support_strength':'weak'}],
      'evidence_anchors':[{'anchor_id':'A001','source_type':'manuscript','section':'body','page_or_location':'body','source_identifier':None,'title':None,'year':None,'quote_or_fact':'claim X','verification_status':'requires_deterministic_validation'}],
      'strengths':[],'major_concerns':[],'minor_concerns':[],'observations':[],
      'novelty_assessment':{'status':'external_verification_required','assessment':'not checked','external_anchor_ids':[]},
      'reproducibility_assessment':{'status':'insufficient_information','assessment':'not enough','missing_requirements':[]},
      'numerical_consistency':{'status':'not_assessable','issues':[]},
      'review_summary':{'central_claims_supported':[],'central_claims_at_risk':['C001'],'strongest_concern_ids':[],'overall_scientific_confidence':0.4,'remaining_uncertainties':[]},
    }


def _concern(*, claim='C001', anchor='A001', title='Concern'):
    return {
      'concern_id':'MC001','title':title,'severity':'major','claim_ids':[claim],'evidence_anchor_ids':[anchor],
      'failure_mechanism':'The cited design cannot establish the stated claim.','scientific_consequence':'The central interpretation is not supported.',
      'minimum_resolution':'Narrow the claim or provide identifying evidence.','closure_criterion':'The claim is narrowed or a valid identification strategy is demonstrated.',
      'reviewer_confidence':0.9,'steelman':'The authors may intend a weaker descriptive interpretation.','steelman_survives':True,
      'steelman_survival_reason':'The current wording remains causal.','external_verification_required':False,'uncertainties':[],'suggested_validation_checks':[]}


def _base_responses(concern, specialist_anchors=None):
    return {
      'classification':{'specialists':['methods_design']},
      'core_peer_review':_core(),
      'review_plan':{'tasks':[{'task_id':'T001','specialist':'methods_design','claim_ids':['C001'],'objective':'audit','priority':'high','evidence_needs':[]}]},
      'numerical_ledger':{'items':[],'concerns':[],'evidence_anchors':[]},
      'literature_plan':{'queries':[]},'literature_synthesis':{'concerns':[],'evidence_anchors':[],'novelty':{},'pivotal_sources':[]},
      'specialist:methods_design':{'concerns':[concern],'evidence_anchors':specialist_anchors or [],'notes':[],'uncertainty':[]},
      'redteam_steelman':{'concerns':[concern],'evidence_anchors':[]},
      'reliability':{'status':'stable'},
      'final_synthesis':{'critical_gates':{},'final_review':{'decision_brief':{},'minor_comments':[],'strengths':[],'limitations':[]}},
      'journal_calibration':{'journals':[]},
    }


def test_unknown_claim_never_reaches_verifier(tmp_path):
    p=tmp_path/'p.md';p.write_text('claim X',encoding='utf-8')
    c=_concern(claim='C404', title='Bad claim reference')
    llm=ScriptedLLMProvider(_base_responses(c))
    e=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=ReviewConfig(mode='deep', pipeline="full", run_root=str(tmp_path/'r')),package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(e.review([str(p)],run_id='x'))
    assert not state.admitted_concerns
    assert any('unknown claims' in ' '.join(x.get('admission_errors',[])) for x in state.rejected_concerns)
    assert not any(call.operation.startswith('concern_verifier:') for call in llm.calls)


def test_nonexistent_anchor_text_fails_before_verifier(tmp_path):
    p=tmp_path/'p.md';p.write_text('claim X',encoding='utf-8')
    c=_concern(anchor='A002', title='Anchor mismatch')
    bad_anchor={'anchor_id':'A002','source_type':'manuscript','document_id':'D1','locator':'body','quote_or_fact':'text that does not exist','supports':'C001','confidence':'high','url':None,'content_status':None,'content_sha256':None}
    llm=ScriptedLLMProvider(_base_responses(c,[bad_anchor]))
    e=ReviewEngine(llm=llm,search=ScriptedSearchProvider(),config=ReviewConfig(mode='deep', pipeline="full", run_root=str(tmp_path/'r')),package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(e.review([str(p)],run_id='x'))
    assert not state.admitted_concerns
    assert any('anchor integrity failed' in ' '.join(x.get('admission_errors',[])) for x in state.rejected_concerns)
    assert not any(call.operation.startswith('concern_verifier:') for call in llm.calls)
