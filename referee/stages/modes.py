from __future__ import annotations
import json
from pathlib import Path

from .base import Stage
from .core import _call, _compact_docs
from ..documents import DocumentLoader
from ..comparison import revision_diff, build_resolution_matrix, audit_rebuttal_structure
from ..contracts import schemas as S


def _load_jsonish(path: str | None):
    if not path:
        return []
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() == ".jsonl":
        return [json.loads(x) for x in text.splitlines() if x.strip()]
    obj = json.loads(text)
    if isinstance(obj, dict) and "concerns" in obj:
        return obj["concerns"]
    return obj if isinstance(obj, list) else [obj]


class RevisionPreparationStage(Stage):
    stage_id = "01c_revision_preparation"
    async def run(self, ctx, state):
        prior_path = state.mode_inputs.get("prior_manuscript")
        old = DocumentLoader().load(prior_path, "PRIOR").text
        current = "\n".join(d.get("text", "") for d in state.document_map.get("documents", []))
        prior_concerns = _load_jsonish(state.mode_inputs.get("prior_concerns"))
        artifact = {
            "prior_manuscript": prior_path,
            "diff": revision_diff(old, current),
            "prior_concerns": prior_concerns,
            "heuristic_resolution_matrix": build_resolution_matrix(prior_concerns, current),
        }
        state.revision_audit = artifact
        state.mode_artifacts["revision_preparation"] = artifact
        ctx.checkpoints.write_artifact("revision_preparation.json", artifact)


class RevisionClosureStage(Stage):
    stage_id = "13a_revision_closure"
    async def run(self, ctx, state):
        prior = state.revision_audit.get("prior_concerns", [])
        out = await _call(
            ctx, "revision_closure",
            "You audit scientific revisions concern by concern. A response is not closure unless the revised manuscript contains the promised scientific change. Detect regressions introduced by the revision.",
            "Return closure_rows, new_regressions, summary.\nPrior concerns:\n" + json.dumps(prior, ensure_ascii=False)[:16000] +
            "\nStructured diff:\n" + json.dumps(state.revision_audit.get("diff", {}), ensure_ascii=False)[:20000] +
            "\nCurrent verified concerns:\n" + json.dumps(state.admitted_concerns, ensure_ascii=False)[:16000] +
            "\nCurrent manuscript:\n" + _compact_docs(state, 18000),
            schema=S.MODE_REVISION,
        )
        state.revision_audit["scientific_closure"] = out
        state.mode_artifacts["revision_closure"] = out
        ctx.checkpoints.write_artifact("revision_closure.json", out)


class RebuttalPreparationStage(Stage):
    stage_id = "01c_rebuttal_preparation"
    async def run(self, ctx, state):
        comments = DocumentLoader().load(state.mode_inputs["reviewer_comments"], "COMMENTS").text
        rebuttal = DocumentLoader().load(state.mode_inputs["rebuttal"], "REBUTTAL").text
        artifact = {
            "reviewer_comments": comments,
            "rebuttal": rebuttal,
            "response_structure": audit_rebuttal_structure(rebuttal),
        }
        state.mode_artifacts["rebuttal_preparation"] = artifact
        ctx.checkpoints.write_artifact("rebuttal_preparation.json", artifact)


class RebuttalClosureStage(Stage):
    stage_id = "13a_rebuttal_closure"
    async def run(self, ctx, state):
        prep = state.mode_artifacts.get("rebuttal_preparation", {})
        out = await _call(
            ctx, "rebuttal_closure",
            "Audit scientific closure, not rhetorical compliance. For each concern compare the scientific problem, author response, promised action, and actual revised-manuscript evidence. A promise without a manuscript change is unresolved. A narrower scientifically sufficient claim can resolve an unnecessary experimental demand. Detect new regressions independently.",
            "Return rows, unresolved, new_regressions, summary. Each row must use resolved|partially_resolved|unresolved|not_assessable and record promise_without_change_detected plus response_without_evidence_detected.\nReviewer comments:\n" + prep.get("reviewer_comments", "")[:16000] +
            "\nAuthor response:\n" + prep.get("rebuttal", "")[:16000] +
            "\nRevised manuscript:\n" + _compact_docs(state, 18000),
            schema=S.MODE_REBUTTAL,
        )
        state.mode_artifacts["rebuttal_closure"] = out
        ctx.checkpoints.write_artifact("rebuttal_closure.json", out)


class MetaReviewStage(Stage):
    stage_id = "20_meta_review"
    async def run(self, ctx, state):
        out = await _call(
            ctx, "meta_review",
            "Synthesize multiple reviewer reports. Preserve disagreement and do not manufacture consensus. Separate repeated concerns from unique concerns and factual conflicts.",
            "Return consensus, disagreements, meta_review.\nReviewer reports:\n" + _compact_docs(state, 30000),
            schema=S.MODE_META,
        )
        state.disagreement_map = {"consensus": out.get("consensus", []), "disagreements": out.get("disagreements", [])}
        state.final_review = {"meta_review": out.get("meta_review", {}), "disagreement_map": state.disagreement_map}
        state.mode_artifacts["meta_review"] = out
        ctx.checkpoints.write_artifact("meta_review.json", out)


class EditorialScreenSynthesisStage(Stage):
    stage_id = "20_editorial_screen"
    async def run(self, ctx, state):
        out = await _call(
            ctx, "editorial_screen",
            "Perform an editorial scientific completeness screen, not a full peer review. Identify only fatal scientific barriers and missing artifacts that justify withholding external review.",
            "Return fatal_barriers, missing_artifacts, screening_report.\nClassification:\n" + json.dumps(state.classification, ensure_ascii=False) +
            "\nPackage audit:\n" + json.dumps(state.package_audit, ensure_ascii=False)[:12000] +
            "\nReporting audit:\n" + json.dumps(state.reporting_audit, ensure_ascii=False)[:12000] +
            "\nNumerical audit:\n" + json.dumps(state.numerical_ledger, ensure_ascii=False)[:12000],
            schema=S.SCREENING,
        )
        state.final_review = out
        state.mode_artifacts["editorial_screen"] = out
        ctx.checkpoints.write_artifact("editorial_screen.json", out)


class ReproducibilitySynthesisStage(Stage):
    stage_id = "20_reproducibility_synthesis"
    async def run(self, ctx, state):
        out = await _call(
            ctx, "reproducibility_synthesis",
            "Assess whether the supplied package is sufficient to reproduce the computational/analytical workflow without executing untrusted code. Distinguish missing evidence from failed reproduction.",
            "Return reproducibility_report and blocking_gaps.\nPackage scan:\n" + json.dumps(state.reproducibility_report, ensure_ascii=False)[:24000] +
            "\nPackage audit:\n" + json.dumps(state.package_audit, ensure_ascii=False)[:12000],
            schema=S.REPRO_SYNTHESIS,
        )
        state.final_review = out
        state.mode_artifacts["reproducibility"] = out
        ctx.checkpoints.write_artifact("reproducibility_synthesis.json", out)
