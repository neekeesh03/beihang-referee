from __future__ import annotations
from typing import Any


def build_quality_snapshot(state: dict[str, Any], workspace: dict[str, Any] | None = None) -> dict[str, Any]:
    claims = {c.get("claim_id") for c in state.get("claims", []) if c.get("claim_id")}
    anchors = {a.get("anchor_id") for a in state.get("evidence_anchors", []) if a.get("anchor_id")}
    concerns = state.get("admitted_concerns", [])
    workspace = workspace or {"concerns": {}}
    invalid_claim_refs = 0
    invalid_anchor_refs = 0
    missing_closure = 0
    high_conf = 0
    statuses: dict[str, int] = {}
    verification={r.get("concern_id"):r for r in state.get("verification_records",[]) if isinstance(r,dict)}
    missing_verification=0;nonindependent_contexts=0;failed_provenance=0
    for c in concerns:
        invalid_claim_refs += sum(1 for cid in c.get("claim_ids", []) if cid not in claims)
        invalid_anchor_refs += sum(1 for aid in c.get("evidence_anchor_ids", []) if aid not in anchors)
        if not str(c.get("closure_criterion", "")).strip():
            missing_closure += 1
        if isinstance(c.get("reviewer_confidence"), (int, float)) and float(c.get("reviewer_confidence")) >= 0.90:
            high_conf += 1
        rec=verification.get(c.get("concern_id"))
        if not rec or rec.get("verification_status")!="verified": missing_verification += 1
        if rec and rec.get("generator_context_id") and rec.get("generator_context_id")==rec.get("verifier_context_id"): nonindependent_contexts += 1
        if (c.get("provenance_gate") or {}).get("status")!="passed": failed_provenance += 1
        human_status = workspace.get("concerns", {}).get(c.get("concern_id", ""), {}).get("status", "open")
        statuses[human_status] = statuses.get(human_status, 0) + 1
    return {
        "status": state.get("status"),
        "claims": len(state.get("claims", [])),
        "evidence_anchors": len(state.get("evidence_anchors", [])),
        "admitted_major_comments": len(concerns),
        "rejected_major_comments": len(state.get("rejected_concerns", [])),
        "invalid_claim_references": invalid_claim_refs,
        "invalid_anchor_references": invalid_anchor_refs,
        "major_comments_missing_closure": missing_closure,
        "high_confidence_major_comments": high_conf,
        "major_comments_missing_verification": missing_verification,
        "nonindependent_verifier_contexts": nonindependent_contexts,
        "major_comments_failed_provenance_gate": failed_provenance,
        "human_concern_statuses": statuses,
        "warnings": len(state.get("warnings", [])),
        "critical_gates": state.get("critical_gates", {}),
        "provenance": state.get("provenance_report", {}),
    }
