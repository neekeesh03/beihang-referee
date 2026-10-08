from pathlib import Path
import asyncio
from referee import ReviewConfig, ReviewEngine
from referee.providers import ScriptedLLMProvider
from referee.providers.base import SearchProvider

class FetchingSearch(SearchProvider):
    def __init__(self): self.calls=[]
    async def search(self, query, *, limit=8):
        self.calls.append(query)
        return [{"url":"https://example.test/source","title":"Source"}]
    async def fetch(self, url):
        return {"url":url,"raw_content":"Independent source content relevant to the concern."}


def test_uncertain_verifier_is_not_promoted_or_allowed_to_search(tmp_path):
    paper=tmp_path/'p.md'; paper.write_text('A causal claim. Methods have no control group.',encoding='utf-8')
    c={
      "concern_id":"MC001","title":"Causal issue","severity":"major","claim_ids":["C001"],"evidence_anchor_ids":["A001"],
      "failure_mechanism":"No counterfactual is available because the study reports no control group.",
      "scientific_consequence":"The causal effect is unidentified.","minimum_resolution":"Reframe the claim as associational or provide a valid identification strategy.",
      "closure_criterion":"Causal language is removed or a valid identification strategy is demonstrated.","reviewer_confidence":0.9,
      "steelman":"The authors may intend the result as a descriptive association.","steelman_survives":True,
      "steelman_survival_reason":"The current wording is still explicitly causal.","external_verification_required":False,
      "uncertainties":[],"suggested_validation_checks":[]}
    core={
      "review_protocol":"beihang-referee","review_mode":"initial",
      "manuscript_summary":{"research_question":"causal claim","approach":"uncontrolled","main_results":"causal claim","claimed_contribution":"causal effect"},
      "claim_registry":[{"claim_id":"C001","claim_text":"A causal claim","claim_type":"causal","importance":"central","location":"body","supporting_evidence":["A001"],"support_strength":"weak"}],
      "evidence_anchors":[{"anchor_id":"A001","source_type":"manuscript","section":"Methods","page_or_location":"body","source_identifier":None,"title":None,"year":None,"quote_or_fact":"no control group","verification_status":"requires_deterministic_validation"}],
      "strengths":[],"major_concerns":[],"minor_concerns":[],"observations":[],
      "novelty_assessment":{"status":"external_verification_required","assessment":"not checked","external_anchor_ids":[]},
      "reproducibility_assessment":{"status":"insufficient_information","assessment":"not enough","missing_requirements":[]},
      "numerical_consistency":{"status":"not_assessable","issues":[]},
      "review_summary":{"central_claims_supported":[],"central_claims_at_risk":["C001"],"strongest_concern_ids":[],"overall_scientific_confidence":0.4,"remaining_uncertainties":[]}}
    responses={
      "classification":{"specialists":["methods_design"]},"core_peer_review":core,
      "review_plan":{"tasks":[{"task_id":"T001","specialist":"methods_design","claim_ids":["C001"],"objective":"audit","priority":"high","evidence_needs":[]}]},
      "numerical_ledger":{"items":[],"concerns":[],"evidence_anchors":[]},
      "literature_plan":{"queries":[]}, "literature_synthesis":{"concerns":[],"evidence_anchors":[],"novelty":{},"pivotal_sources":[]},
      "specialist:methods_design":{"concerns":[c],"evidence_anchors":[],"notes":[],"uncertainty":[]},
      "redteam_steelman":{"concerns":[c],"evidence_anchors":[]},
      "entailment:MC001":{"status":"supported","rationale":"The anchor supports the design limitation.","consequence_proportionate":True,"closure_testable":True},
      "concern_verifier:MC001":{"status":"uncertain","rationale":"The supplied bundle is insufficient to decide.","entailment":{
        "claim_mapping_valid":True,"anchors_support_failure_mechanism":True,"scientific_consequence_proportionate":True,
        "minimum_resolution_sufficient":True,"closure_criterion_testable":True,"steelman_survival_supported":True,
        "manuscript_contradiction_found":False},"uncertainties":["design details incomplete"]},
      "reliability":{"status":"stable"},
      "final_synthesis":{"critical_gates":{},"final_review":{"decision_brief":{},"minor_comments":[],"strengths":[],"limitations":[]}},
      "journal_calibration":{"journals":[]}}
    search=FetchingSearch()
    cfg=ReviewConfig(mode='deep', pipeline="full", run_root=str(tmp_path/'runs'))
    e=ReviewEngine(llm=ScriptedLLMProvider(responses),search=search,config=cfg,package_root=str(Path(__file__).resolve().parents[2]))
    state=asyncio.run(e.review([str(paper)],run_id='x'))
    assert not state.admitted_concerns
    assert state.verification_records[0]['verification_status']=='uncertain'
    assert state.verification_records[0]['deterministic_postcheck']['model_status_trusted_as_proof'] is False
    # The independent judge cannot ask for or trigger a search; search is a separate literature stage.
    assert search.calls==[]
