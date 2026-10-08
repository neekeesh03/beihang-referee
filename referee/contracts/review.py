from __future__ import annotations
from typing import Any
from .schemas import obj, arr, STR, STR_NULL, BOOL, NUM, FREE_OBJ, FREE_ARR, EVIDENCE_ANCHOR, CLAIM

CORE_CANDIDATE_CONCERN = obj({
    "concern_id": STR,
    "title": STR,
    "severity": {"enum": ["major", "minor", "observation"]},
    "claim_ids": arr(STR),
    "evidence_anchor_ids": arr(STR),
    "failure_mechanism": STR,
    "scientific_consequence": STR,
    "minimum_resolution": STR,
    "closure_criterion": STR,
    "reviewer_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "external_verification_required": BOOL,
    "uncertainties": arr(STR),
    "suggested_validation_checks": arr(STR),
}, [
    "concern_id", "title", "severity", "claim_ids", "evidence_anchor_ids",
    "failure_mechanism", "scientific_consequence", "minimum_resolution",
    "closure_criterion", "reviewer_confidence", "external_verification_required",
    "uncertainties", "suggested_validation_checks",
])

CORE_SPECIALIST_REQUEST = obj({
    "task_id": STR,
    "specialist": STR,
    "claim_ids": arr(STR),
    "objective": STR,
    "priority": {"enum": ["high", "medium", "low"]},
    "evidence_needs": arr(STR),
}, ["task_id", "specialist", "claim_ids", "objective", "priority", "evidence_needs"])

CORE_LITERATURE_QUERY = obj({
    "query": STR,
    "goal": STR,
    "claim_ids": arr(STR),
}, ["query", "goal", "claim_ids"])

CORE_REVIEW_OUTPUT = obj({
    "review_protocol": {"const": "beihang-referee"},
    "classification": obj({
        "field": STR,
        "domain": STR,
        "design": STR,
        "inference_type": STR,
        "study_type": STR,
    }, ["field", "domain", "design", "inference_type", "study_type"], additional=True),
    "manuscript_summary": obj({
        "research_question": STR,
        "approach": STR,
        "main_results": STR,
        "claimed_contribution": STR,
        "developmental_stage": STR,
    }, ["research_question", "approach", "main_results", "claimed_contribution", "developmental_stage"]),
    "claims": arr(CLAIM),
    "evidence_anchors": arr(EVIDENCE_ANCHOR),
    "candidate_concerns": arr(CORE_CANDIDATE_CONCERN),
    "minor_concerns": FREE_ARR,
    "strengths": FREE_ARR,
    "observations": FREE_ARR,
    "literature_queries": arr(CORE_LITERATURE_QUERY),
    "specialist_requests": arr(CORE_SPECIALIST_REQUEST),
    "overall_scientific_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "remaining_uncertainties": arr(STR),
}, [
    "review_protocol", "classification", "manuscript_summary", "claims", "evidence_anchors",
    "candidate_concerns", "minor_concerns", "strengths", "observations",
    "literature_queries", "specialist_requests", "overall_scientific_confidence",
    "remaining_uncertainties",
])

CORE_SPECIALIST_RESULT = obj({
    "candidate_concerns": arr(CORE_CANDIDATE_CONCERN),
    "evidence_anchors": arr(EVIDENCE_ANCHOR),
    "notes": FREE_ARR,
    "uncertainties": FREE_ARR,
}, ["candidate_concerns", "evidence_anchors", "notes", "uncertainties"])

CORE_VERIFIER_ENTAILMENT = obj({
    "claim_mapping_valid": BOOL,
    "anchors_support_failure_mechanism": BOOL,
    "scientific_consequence_proportionate": BOOL,
    "minimum_resolution_sufficient": BOOL,
    "closure_criterion_testable": BOOL,
    "steelman_survival_supported": BOOL,
    "manuscript_contradiction_found": BOOL,
}, [
    "claim_mapping_valid", "anchors_support_failure_mechanism",
    "scientific_consequence_proportionate", "minimum_resolution_sufficient",
    "closure_criterion_testable", "steelman_survival_supported",
    "manuscript_contradiction_found",
])

CORE_VERIFIER = obj({
    "status": {"enum": ["verified", "downgrade", "rejected", "needs_evidence"]},
    "severity": {"enum": ["major", "minor", "observation"]},
    "steelman": STR,
    "steelman_survives": BOOL,
    "steelman_survival_reason": STR,
    "rationale": STR,
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "entailment": CORE_VERIFIER_ENTAILMENT,
    "uncertainties": arr(STR),
}, [
    "status", "severity", "steelman", "steelman_survives", "steelman_survival_reason",
    "rationale", "confidence", "entailment", "uncertainties",
])

CORE_SCORE_ITEM = obj({
    "dimension": STR,
    "score": {"enum": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "N/A"]},
    "justification": STR,
    "evidence_basis": arr(STR),
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
}, ["dimension", "score", "justification", "evidence_basis", "confidence"])

CORE_SCORECARD = obj({
    "scientific_gates": FREE_OBJ,
    "dimensions": arr(CORE_SCORE_ITEM),
    "calibration_note": STR,
    "measurement_status": {"enum": ["diagnostic_ordinal_uncalibrated", "benchmark_referenced"]},
    "precision_warning": STR,
}, ["scientific_gates", "dimensions", "calibration_note", "measurement_status", "precision_warning"])

CORE_TARGET_JOURNAL = obj({
    "target_journal": STR,
    "fit_score": {"type": "number", "minimum": 1.0, "maximum": 10.0},
    "impact_potential_score": {"type": "number", "minimum": 1.0, "maximum": 10.0},
    "publication_readiness_score": {"type": "number", "minimum": 1.0, "maximum": 10.0},
    "audience_fit": STR,
    "contribution_threshold": STR,
    "major_mismatch": STR_NULL,
    "evidence_status": {"enum": ["frozen_official_profile", "provisional_model_prior"]},
    "profile_source_count": {"type": "integer", "minimum": 0},
    "evidence_basis": arr(STR),
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
}, [
    "target_journal", "fit_score", "impact_potential_score", "publication_readiness_score",
    "audience_fit", "contribution_threshold", "major_mismatch", "evidence_status",
    "profile_source_count", "evidence_basis", "confidence",
])
