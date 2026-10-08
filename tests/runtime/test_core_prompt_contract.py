from referee.contracts.core_review import validate_and_materialize_core_review


def _review(anchor_text="observed fact"):
    return {
      "review_protocol":"beihang-referee","review_mode":"initial",
      "manuscript_summary":{"research_question":"Q","approach":"A","main_results":"R","claimed_contribution":"C"},
      "claim_registry":[{"claim_id":"C001","claim_text":"A claim","claim_type":"descriptive","importance":"central","location":"body","supporting_evidence":["A001"],"support_strength":"moderate"}],
      "evidence_anchors":[{"anchor_id":"A001","source_type":"manuscript","section":"body","page_or_location":"body","source_identifier":None,"title":None,"year":None,"quote_or_fact":anchor_text,"verification_status":"requires_deterministic_validation"}],
      "strengths":[],"major_concerns":[],"minor_concerns":[],"observations":[],
      "novelty_assessment":{"status":"external_verification_required","assessment":"unverified","external_anchor_ids":[]},
      "reproducibility_assessment":{"status":"insufficient_information","assessment":"unknown","missing_requirements":[]},
      "numerical_consistency":{"status":"not_assessable","issues":[]},
      "review_summary":{"central_claims_supported":[],"central_claims_at_risk":[],"strongest_concern_ids":[],"overall_scientific_confidence":0.5,"remaining_uncertainties":[]}}


def test_model_anchor_verification_field_is_never_trusted():
    review=_review("invented quote")
    errors, claims, anchors, audit=validate_and_materialize_core_review(review,review_mode="initial",documents=[{"document_id":"D1","text":"observed fact"}],verified_external_evidence=[])
    assert errors
    assert audit["model_verification_status_trusted"] is False
    assert audit["anchor_validation"]["A001"]["status"] == "invalid"
    assert audit["anchor_validation"]["A001"]["model_verification_status_ignored"] == "requires_deterministic_validation"


def test_core_anchor_is_deterministically_materialized_from_manuscript():
    errors, claims, anchors, audit=validate_and_materialize_core_review(_review(),review_mode="initial",documents=[{"document_id":"D1","text":"The observed fact is present."}],verified_external_evidence=[])
    assert errors == []
    assert anchors[0]["document_id"] == "D1"
    assert anchors[0]["deterministic_verification_status"] == "verified"
