from __future__ import annotations
from pathlib import Path

from .base import Stage
from ..ingestion import PackageInspector
from ..reporting import GuidelineRegistry, heuristic_checklist
from ..reproducibility import scan_reproducibility_package
from ..reviewers.consensus import consensus_summary
from ..reviewers.disagreement import disagreement_map
from ..verification import verify_anchor_integrity, provenance_score, assess_closure_test


class PackageAuditStage(Stage):
    stage_id = "01b_package_audit"

    async def run(self, ctx, state):
        if not ctx.config.enable_package_audit:
            return
        audit = PackageInspector().inspect(state.manuscript_paths).to_dict()
        state.package_audit = audit
        state.warnings.extend(audit.get("warnings", []))
        ctx.checkpoints.write_artifact("package_audit.json", audit)


class ReportingAuditStage(Stage):
    stage_id = "03b_reporting_audit"

    async def run(self, ctx, state):
        if not ctx.config.enable_reporting_audit:
            return
        root = ctx.package_root / "profiles" / "guidelines"
        registry = GuidelineRegistry(root)
        routed = registry.route(state.classification)
        manuscript_text = "\n".join(d.get("text", "") for d in state.document_map.get("documents", []))
        selected = []
        for hit in routed[:4]:
            selected.append({
                "name": hit["name"],
                "routing_score": hit["score"],
                "audit": heuristic_checklist(manuscript_text, hit["profile"]),
            })
        state.reporting_audit = {
            "selected_profiles": selected,
            "authoritative_checklist_required": True,
            "formal_compliance_claimed": False,
        }
        ctx.checkpoints.write_artifact("reporting_audit.json", state.reporting_audit)


class ReproducibilityAuditStage(Stage):
    stage_id = "06b_reproducibility"

    async def run(self, ctx, state):
        if not ctx.config.enable_reproducibility_audit:
            return
        state.reproducibility_report = scan_reproducibility_package(state.manuscript_paths)
        ctx.checkpoints.write_artifact("reproducibility_report.json", state.reproducibility_report)


class DisagreementAuditStage(Stage):
    stage_id = "08b_reviewer_disagreement"

    async def run(self, ctx, state):
        if not ctx.config.enable_disagreement_audit:
            return
        state.disagreement_map = {
            "consensus": consensus_summary(state.specialist_results),
            "disagreement": disagreement_map(state.specialist_results),
        }
        ctx.checkpoints.write_artifact("reviewer_disagreement.json", state.disagreement_map)


class ProvenanceAuditStage(Stage):
    stage_id = "11b_provenance_audit"

    async def run(self, ctx, state):
        if not ctx.config.enable_provenance_audit:
            return
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        anchor_integrity = verify_anchor_integrity(state.evidence_anchors, state.document_map.get("documents", []))
        concern_rows = []
        for c in state.admitted_concerns:
            row = provenance_score(c, anchor_by_id)
            row["closure"] = assess_closure_test(c.get("closure_criterion", ""))
            concern_rows.append(row)
        invalid_ids={r.get("anchor_id") for r in anchor_integrity.get("anchors",[]) if r.get("status") not in {"verified","external_verified"}}
        state.provenance_report = {
            "anchor_integrity": anchor_integrity,
            "major_concerns": concern_rows,
            "all_major_concerns_have_resolved_anchors": all(r["resolved_anchor_count"] == r["anchor_count"] for r in concern_rows) if concern_rows else True,
            "all_cited_major_anchors_integrity_verified": all(not (set(c.get("evidence_anchor_ids",[])) & invalid_ids) for c in state.admitted_concerns),
            "verification_records": state.verification_records,
            "hard_gate_preceded_admission": True,
        }
        ctx.checkpoints.write_artifact("provenance_report.json", state.provenance_report)
