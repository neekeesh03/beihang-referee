from __future__ import annotations
from typing import Any
from .concern import concern_json_schema


def obj(properties: dict[str, Any], required: list[str] | None = None, *, additional: bool = False) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": additional, "properties": properties, "required": required or []}

def arr(items: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "array", "items": items or {}}

STR = {"type": "string"}
STR_NULL = {"type": ["string", "null"]}
BOOL = {"type": "boolean"}
NUM = {"type": "number"}
FREE_OBJ = {"type": "object", "additionalProperties": True}
FREE_ARR = {"type": "array", "items": {}}

# Internal evidence/claim contracts used by specialist and search stages.
EVIDENCE_ANCHOR = obj({
    "anchor_id": STR, "source_type": STR, "document_id": STR, "locator": STR,
    "quote_or_fact": STR, "supports": STR, "confidence": STR,
    "url": STR_NULL, "content_status": STR_NULL, "content_sha256": STR_NULL,
}, ["anchor_id", "source_type", "document_id", "locator", "quote_or_fact", "supports", "confidence"], additional=False)

CLAIM = obj({
    "claim_id": STR, "text": STR, "claim_type": STR, "centrality": STR, "scope": STR,
    "proof_burden": arr(STR), "evidence_anchor_ids": arr(STR), "support_status": STR,
    "confidence": STR, "alternatives": arr(STR),
}, ["claim_id", "text", "claim_type", "centrality"], additional=False)

CONCERN = concern_json_schema()

# Exact core peer-review output contract from PEER_REVIEW_PROMPT.md.
CORE_CLAIM = obj({
    "claim_id": {"type": "string", "pattern": "^C[0-9]{3,}$"},
    "claim_text": STR,
    "claim_type": {"enum": ["descriptive", "associational", "causal", "predictive", "mechanistic", "comparative", "methodological", "theoretical", "novelty", "generalisability", "other"]},
    "importance": {"enum": ["central", "supporting", "peripheral"]},
    "location": STR,
    "supporting_evidence": arr({"type": "string", "pattern": "^A[0-9]{3,}$"}),
    "support_strength": {"enum": ["strong", "moderate", "weak", "unclear", "unsupported"]},
}, ["claim_id", "claim_text", "claim_type", "importance", "location", "supporting_evidence", "support_strength"])

CORE_EVIDENCE_ANCHOR = obj({
    "anchor_id": {"type": "string", "pattern": "^A[0-9]{3,}$"},
    "source_type": {"enum": ["manuscript", "external"]},
    "section": STR,
    "page_or_location": STR,
    "source_identifier": STR_NULL,
    "title": STR_NULL,
    "year": {"type": ["integer", "string", "null"]},
    "quote_or_fact": STR,
    "verification_status": {"const": "requires_deterministic_validation"},
}, ["anchor_id", "source_type", "section", "page_or_location", "source_identifier", "title", "year", "quote_or_fact", "verification_status"])

CORE_STRENGTH = obj({"strength": STR, "claim_ids": arr(STR), "anchor_ids": arr(STR)}, ["strength", "claim_ids", "anchor_ids"])
CORE_MINOR = obj({
    "concern_id": {"type": "string", "pattern": "^MI[0-9]{3,}$"}, "title": STR,
    "severity": {"const": "minor"}, "claim_ids": arr(STR), "evidence_anchor_ids": arr(STR),
    "issue": STR, "consequence": STR, "resolution": STR,
    "reviewer_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
}, ["concern_id", "title", "severity", "claim_ids", "evidence_anchor_ids", "issue", "consequence", "resolution", "reviewer_confidence"])
CORE_OBSERVATION = obj({
    "observation_id": {"type": "string", "pattern": "^O[0-9]{3,}$"}, "text": STR,
    "claim_ids": arr(STR), "evidence_anchor_ids": arr(STR),
}, ["observation_id", "text", "claim_ids", "evidence_anchor_ids"])
CORE_NOVELTY = obj({
    "status": {"enum": ["supported", "questioned", "external_verification_required", "not_applicable"]},
    "assessment": STR, "external_anchor_ids": arr(STR),
}, ["status", "assessment", "external_anchor_ids"])
CORE_REPRO = obj({
    "status": {"enum": ["reproducible", "partially_reproducible", "insufficient_information", "not_applicable"]},
    "assessment": STR, "missing_requirements": arr(STR),
}, ["status", "assessment", "missing_requirements"])
CORE_NUMERICAL = obj({"status": {"enum": ["consistent", "issues_found", "not_assessable"]}, "issues": FREE_ARR}, ["status", "issues"])
CORE_SUMMARY = obj({
    "central_claims_supported": arr(STR), "central_claims_at_risk": arr(STR), "strongest_concern_ids": arr(STR),
    "overall_scientific_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "remaining_uncertainties": arr(STR),
}, ["central_claims_supported", "central_claims_at_risk", "strongest_concern_ids", "overall_scientific_confidence", "remaining_uncertainties"])
CORE_PEER_REVIEW_OUTPUT = obj({
    "review_protocol": {"const": "beihang-referee"},
    "review_mode": {"enum": ["initial", "revision", "rebuttal", "meta_review", "editorial_screen", "reproducibility"]},
    "manuscript_summary": obj({"research_question": STR, "approach": STR, "main_results": STR, "claimed_contribution": STR}, ["research_question", "approach", "main_results", "claimed_contribution"]),
    "claim_registry": arr(CORE_CLAIM),
    "evidence_anchors": arr(CORE_EVIDENCE_ANCHOR),
    "strengths": arr(CORE_STRENGTH),
    "major_concerns": arr(CONCERN),
    "minor_concerns": arr(CORE_MINOR),
    "observations": arr(CORE_OBSERVATION),
    "novelty_assessment": CORE_NOVELTY,
    "reproducibility_assessment": CORE_REPRO,
    "numerical_consistency": CORE_NUMERICAL,
    "review_summary": CORE_SUMMARY,
}, ["review_protocol", "review_mode", "manuscript_summary", "claim_registry", "evidence_anchors", "strengths", "major_concerns", "minor_concerns", "observations", "novelty_assessment", "reproducibility_assessment", "numerical_consistency", "review_summary"])

CLASSIFICATION = obj({
    "field": STR, "design": STR, "inference_type": STR, "specialists": arr(STR),
    "domain": STR, "novelty_assessment": FREE_OBJ,
}, ["specialists"], additional=True)
CLAIM_REGISTRY = obj({"claims": arr(CLAIM), "evidence_anchors": arr(EVIDENCE_ANCHOR)}, ["claims", "evidence_anchors"])
REVIEW_TASK = obj({
    "task_id": STR, "specialist": STR, "claim_ids": arr(STR), "objective": STR,
    "priority": STR, "evidence_needs": arr(STR),
}, ["task_id", "specialist", "claim_ids", "objective", "priority", "evidence_needs"], additional=False)
REVIEW_PLAN = obj({"tasks": arr(REVIEW_TASK)}, ["tasks"])
NUMERICAL = obj({"items": FREE_ARR, "concerns": arr(CONCERN), "evidence_anchors": arr(EVIDENCE_ANCHOR)}, ["items", "concerns", "evidence_anchors"])
LITERATURE_QUERY = obj({"query": STR, "goal": STR, "claim_ids": arr(STR)}, ["query", "goal", "claim_ids"], additional=False)
LITERATURE_PLAN = obj({"queries": arr(LITERATURE_QUERY)}, ["queries"])
LITERATURE_SYNTHESIS = obj({
    "concerns": arr(CONCERN), "evidence_anchors": arr(EVIDENCE_ANCHOR), "novelty": FREE_OBJ, "pivotal_sources": FREE_ARR,
}, ["concerns", "evidence_anchors", "novelty", "pivotal_sources"])
SPECIALIST_RESULT = obj({"concerns": arr(CONCERN), "evidence_anchors": arr(EVIDENCE_ANCHOR), "notes": FREE_ARR, "uncertainty": FREE_ARR}, ["concerns", "evidence_anchors", "notes", "uncertainty"])
REDTEAM_RESULT = obj({"concerns": arr(CONCERN), "evidence_anchors": arr(EVIDENCE_ANCHOR)}, ["concerns", "evidence_anchors"])
ENTAILMENT = obj({
    "status": {"enum": ["supported", "partial", "unsupported"]}, "rationale": STR,
    "consequence_proportionate": BOOL, "closure_testable": BOOL,
}, ["status", "rationale", "consequence_proportionate", "closure_testable"])
VERIFIER_ENTAILMENT = obj({
    "claim_mapping_valid": BOOL,
    "anchors_support_failure_mechanism": BOOL,
    "scientific_consequence_proportionate": BOOL,
    "minimum_resolution_sufficient": BOOL,
    "closure_criterion_testable": BOOL,
    "steelman_survival_supported": BOOL,
    "manuscript_contradiction_found": BOOL,
}, ["claim_mapping_valid", "anchors_support_failure_mechanism", "scientific_consequence_proportionate", "minimum_resolution_sufficient", "closure_criterion_testable", "steelman_survival_supported", "manuscript_contradiction_found"])
VERIFIER = obj({
    "status": {"enum": ["verified", "rejected", "uncertain"]},
    "rationale": STR, "entailment": VERIFIER_ENTAILMENT, "uncertainties": arr(STR),
}, ["status", "rationale", "entailment", "uncertainties"])
TRAJECTORY = obj({
    "position": {"enum": ["supports", "rejects", "uncertain"]}, "rationale": STR,
    "severity": STR_NULL, "confidence": STR,
}, ["position", "rationale", "severity", "confidence"])
TRAJECTORY_CONSENSUS = obj({
    "agreement": STR, "key_disagreement": STR_NULL, "priority_signal": STR_NULL,
    "do_not_use_for_validity": BOOL,
}, ["agreement", "key_disagreement", "priority_signal", "do_not_use_for_validity"])
PAIRWISE = obj({"winner": STR, "rationale": STR}, ["winner", "rationale"])
RELIABILITY = obj({"status": STR, "stability": STR_NULL, "agreements": FREE_ARR, "disagreements": FREE_ARR, "downgrade_recommendations": FREE_ARR}, ["status"], additional=False)
FINAL_REVIEW = obj({
    "decision_brief": FREE_OBJ, "minor_comments": FREE_ARR, "strengths": FREE_ARR, "limitations": FREE_ARR,
}, ["decision_brief", "minor_comments", "strengths", "limitations"])
FINAL_SYNTHESIS = obj({"critical_gates": FREE_OBJ, "final_review": FINAL_REVIEW}, ["critical_gates", "final_review"])
JOURNAL = obj({"journals": FREE_ARR}, ["journals"])
POLICY = obj({"status": STR, "blocking_condition": STR_NULL, "evidence": FREE_ARR}, ["status", "blocking_condition", "evidence"], additional=True)
MODE_REVISION = obj({"closure_rows": FREE_ARR, "new_regressions": FREE_ARR, "summary": FREE_OBJ}, ["closure_rows", "new_regressions", "summary"])
REBUTTAL_ROW = obj({
    "concern_id": STR,
    "resolution_status": {"enum": ["resolved", "partially_resolved", "unresolved", "not_assessable"]},
    "promised_action": STR,
    "manuscript_evidence": arr(STR),
    "scientific_rationale": STR,
    "promise_without_change_detected": BOOL,
    "response_without_evidence_detected": BOOL,
}, ["concern_id", "resolution_status", "promised_action", "manuscript_evidence", "scientific_rationale", "promise_without_change_detected", "response_without_evidence_detected"])
MODE_REBUTTAL = obj({"rows": arr(REBUTTAL_ROW), "unresolved": FREE_ARR, "new_regressions": FREE_ARR, "summary": FREE_OBJ}, ["rows", "unresolved", "new_regressions", "summary"])
MODE_META = obj({"consensus": FREE_ARR, "disagreements": FREE_ARR, "meta_review": FREE_OBJ}, ["consensus", "disagreements", "meta_review"])
SCREENING = obj({"fatal_barriers": FREE_ARR, "missing_artifacts": FREE_ARR, "screening_report": FREE_OBJ}, ["fatal_barriers", "missing_artifacts", "screening_report"])
REPRO_SYNTHESIS = obj({"reproducibility_report": FREE_OBJ, "blocking_gaps": FREE_ARR}, ["reproducibility_report", "blocking_gaps"])
