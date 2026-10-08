from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

class Severity(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"

class Confidence(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNASSESSABLE = "unassessable"

@dataclass(slots=True)
class EvidenceAnchor:
    anchor_id: str
    source_type: str
    document_id: str
    locator: str
    quote_or_fact: str
    supports: str
    confidence: str = "high"

@dataclass(slots=True)
class Claim:
    claim_id: str
    text: str
    claim_type: str
    centrality: str
    scope: str = ""
    proof_burden: list[str] = field(default_factory=list)
    evidence_anchor_ids: list[str] = field(default_factory=list)
    support_status: str = "unassessed"
    confidence: str = "unassessed"
    alternatives: list[str] = field(default_factory=list)

from .contracts.concern import Concern

@dataclass(slots=True)
class StageRecord:
    stage_id: str
    status: str
    attempt: int
    started_at: str
    finished_at: str | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)

@dataclass(slots=True)
class ReviewState:
    run_id: str
    query: str
    manuscript_paths: list[str]
    mode: str
    review_mode: str = "initial"
    status: str = "created"
    final_review_exportable: bool = True
    hard_invariant_failures: list[dict[str, Any]] = field(default_factory=list)
    soft_invariant_failures: list[dict[str, Any]] = field(default_factory=list)
    current_stage: str | None = None
    policy_status: dict[str, Any] = field(default_factory=dict)
    document_map: dict[str, Any] = field(default_factory=dict)
    package_audit: dict[str, Any] = field(default_factory=dict)
    reporting_audit: dict[str, Any] = field(default_factory=dict)
    reproducibility_report: dict[str, Any] = field(default_factory=dict)
    disagreement_map: dict[str, Any] = field(default_factory=dict)
    provenance_report: dict[str, Any] = field(default_factory=dict)
    revision_audit: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    core_review: dict[str, Any] = field(default_factory=dict)
    core_review_validation: dict[str, Any] = field(default_factory=dict)
    claims: list[dict[str, Any]] = field(default_factory=list)
    review_plan: list[dict[str, Any]] = field(default_factory=list)
    evidence_anchors: list[dict[str, Any]] = field(default_factory=list)
    numerical_ledger: list[dict[str, Any]] = field(default_factory=list)
    search_ledger: list[dict[str, Any]] = field(default_factory=list)
    external_evidence: list[dict[str, Any]] = field(default_factory=list)
    citation_verification_records: list[dict[str, Any]] = field(default_factory=list)
    specialist_results: dict[str, Any] = field(default_factory=dict)
    proposed_concerns: list[dict[str, Any]] = field(default_factory=list)
    provenance_candidates: list[dict[str, Any]] = field(default_factory=list)
    verification_candidates: list[dict[str, Any]] = field(default_factory=list)
    verification_records: list[dict[str, Any]] = field(default_factory=list)
    trajectory_consensus: dict[str, Any] = field(default_factory=dict)
    priority_ranking: list[dict[str, Any]] = field(default_factory=list)
    literature_status: dict[str, Any] = field(default_factory=dict)
    mode_inputs: dict[str, Any] = field(default_factory=dict)
    mode_artifacts: dict[str, Any] = field(default_factory=dict)
    admitted_concerns: list[dict[str, Any]] = field(default_factory=list)
    rejected_concerns: list[dict[str, Any]] = field(default_factory=list)
    critical_gates: dict[str, Any] = field(default_factory=dict)
    reliability: dict[str, Any] = field(default_factory=dict)
    journal_landscape: list[dict[str, Any]] = field(default_factory=list)
    final_review: dict[str, Any] = field(default_factory=dict)
    stage_records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewState":
        return cls(**data)
