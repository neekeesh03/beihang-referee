from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import hashlib
from dataclasses import asdict
import uuid
from typing import Iterable

from .config import ReviewConfig
from .context import RunContext
from .models import ReviewState, StageRecord
from .providers.base import LLMProvider, SearchProvider
from .runtime.events import EventBus
from .runtime.checkpoint import CheckpointStore
from .runtime.budget import Budget
from .runtime.retry import with_retry
from .prompting import PromptLibrary
from .stages import DEFAULT_STAGES, stages_for_mode
from .validation import validate_state_consistency, evaluate_state_invariants
from .renderers.markdown import render_review_markdown
from .evidence import build_evidence_graph_dot
from .exports import render_html, export_concerns_csv
from .utils.hashing import stable_json_hash
from .lifecycle import RunRegistry
from ._resources import resource_root


def _slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:50] or "review"

class ReviewEngine:
    """Resumable execution engine for the evidence-locked peer-review graph."""
    def __init__(self, *, llm: LLMProvider, search: SearchProvider | None = None,
                 config: ReviewConfig | None = None, package_root: str | Path | None = None,
                 stages: Iterable | None = None):
        self.config = config or ReviewConfig()
        self.llm = llm
        self.search = search
        self.package_root = Path(package_root) if package_root else resource_root()
        self._explicit_stages = list(stages) if stages is not None else None
        self.stages = list(stages) if stages is not None else list(DEFAULT_STAGES)

    def _make_context(self, run_dir: Path) -> RunContext:
        events = EventBus(run_dir / "events.jsonl")
        checkpoints = CheckpointStore(run_dir)
        if self.config.pipeline == "core":
            llm_cap = {"standard": 12, "deep": 30, "exhaustive": 80}[self.config.mode]
        else:
            llm_cap = {"standard": 80, "deep": 160, "exhaustive": 320}[self.config.mode]
        budget = Budget(
            llm_calls_max=llm_cap,
            search_calls_max=max(10, self.config.literature_query_budget * 2),
        )
        return RunContext(
            config=self.config,
            package_root=self.package_root,
            run_dir=run_dir,
            llm=self.llm,
            search=self.search,
            events=events,
            checkpoints=checkpoints,
            budget=budget,
            prompts=PromptLibrary(self.package_root),
        )

    async def review(self, manuscript_paths: list[str], *, query: str = "Scientific peer review",
                     run_id: str | None = None, resume: bool = False,
                     mode_inputs: dict[str, str] | None = None) -> ReviewState:
        if not manuscript_paths:
            raise ValueError("At least one input path is required")
        mode_inputs = dict(mode_inputs or {})
        required_mode_inputs = {
            "revision": {"prior_manuscript"},
            "rebuttal": {"reviewer_comments", "rebuttal"},
        }.get(self.config.review_mode, set())
        missing_mode_inputs = sorted(k for k in required_mode_inputs if not mode_inputs.get(k))
        if missing_mode_inputs:
            raise ValueError(f"Review mode {self.config.review_mode} requires mode inputs: {missing_mode_inputs}")
        stages = list(self._explicit_stages) if self._explicit_stages is not None else stages_for_mode(self.config.review_mode, self.config.pipeline)
        run_id = run_id or f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{_slug(query)}-{uuid.uuid4().hex[:6]}"
        run_dir = Path(self.config.run_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        ctx = self._make_context(run_dir)
        registry = RunRegistry(self.config.run_root)
        registry.upsert(
            run_id, status="starting", review_mode=self.config.review_mode, depth_mode=self.config.mode,
            query=query, input_count=len(manuscript_paths),
        )

        if resume and (run_dir / "state.json").exists():
            state = ctx.checkpoints.load_latest()
            completed = {r.get("stage_id") for r in state.stage_records if r.get("status") == "completed"}
        else:
            state = ReviewState(run_id=run_id, query=query, manuscript_paths=manuscript_paths, mode=self.config.mode, review_mode=self.config.review_mode, mode_inputs=mode_inputs)
            completed = set()
            (run_dir / "config.json").write_text(json.dumps(self.config.to_dict(), indent=2), encoding="utf-8")
            input_manifest = []
            manifest_paths = list(manuscript_paths) + [v for v in mode_inputs.values() if isinstance(v, str) and Path(v).exists()]
            for raw_path in manifest_paths:
                fp = Path(raw_path)
                payload = fp.read_bytes()
                input_manifest.append({
                    "path": str(fp),
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                })
            (run_dir / "inputs.json").write_text(json.dumps(input_manifest, indent=2), encoding="utf-8")

        state.status = "running"
        registry.upsert(
            state.run_id, status=state.status, review_mode=self.config.review_mode, depth_mode=self.config.mode,
            query=state.query, input_count=len(state.manuscript_paths),
        )
        for stage in stages:
            if stage.stage_id in completed:
                continue
            state.current_stage = stage.stage_id
            start = datetime.now(timezone.utc).isoformat()
            record = StageRecord(stage.stage_id, "running", 1, start)
            state.stage_records.append(asdict(record))
            ctx.events.emit(type="stage_start", run_id=state.run_id, stage=stage.stage_id, message=f"Starting {stage.stage_id}")

            async def invoke():
                await stage.run(ctx, state)

            try:
                await with_retry(invoke, retries=self.config.max_stage_retries)
                state.stage_records[-1]["status"] = "completed"
                state.stage_records[-1]["finished_at"] = datetime.now(timezone.utc).isoformat()
                if self.config.checkpoint_each_stage:
                    ctx.checkpoints.save_state(state, stage.stage_id)
                ctx.events.emit(type="stage_complete", run_id=state.run_id, stage=stage.stage_id, message=f"Completed {stage.stage_id}")
            except Exception as exc:
                state.stage_records[-1]["status"] = "failed"
                state.stage_records[-1]["finished_at"] = datetime.now(timezone.utc).isoformat()
                state.stage_records[-1]["error"] = f"{type(exc).__name__}: {exc}"
                state.status = "failed"
                ctx.checkpoints.save_state(state, f"{stage.stage_id}-failed")
                ctx.events.emit(type="stage_failed", run_id=state.run_id, stage=stage.stage_id, message=str(exc), data={"exception": type(exc).__name__})
                registry.upsert(
                    state.run_id, status="failed", review_mode=self.config.review_mode, depth_mode=self.config.mode,
                    query=state.query, input_count=len(state.manuscript_paths),
                    summary={"failed_stage": stage.stage_id, "error": f"{type(exc).__name__}: {exc}"},
                )
                raise

        state.current_stage = None
        state.status = "completed"
        state.metrics.update({
            "llm_calls": ctx.budget.llm_calls,
            "search_calls": ctx.budget.search_calls,
            "pipeline": self.config.pipeline,
            "admitted_major_comments": len(state.admitted_concerns),
            "rejected_major_comments": len(state.rejected_concerns),
            "specialists_run": len(state.specialist_results),
        })
        invariant_report = evaluate_state_invariants(state.to_dict())
        state.hard_invariant_failures = invariant_report["hard_invariant_failures"]
        state.soft_invariant_failures = invariant_report["soft_invariant_failures"]
        state.final_review_exportable = bool(invariant_report["final_review_exportable"])
        state.warnings.extend(x["message"] for x in state.soft_invariant_failures)
        if state.hard_invariant_failures:
            state.status = "failed_validation"
        elif state.soft_invariant_failures:
            state.status = "completed_with_validation_warnings"
        ctx.checkpoints.save_state(state, "99_complete")
        ctx.checkpoints.write_artifact("validation_status.json", invariant_report)
        ctx.checkpoints.write_artifact("concern_admission_log.json", {"admitted": state.admitted_concerns, "rejected": state.rejected_concerns})
        ctx.checkpoints.write_artifact("evidence_graph.dot", build_evidence_graph_dot(state.to_dict()))
        if state.final_review_exportable:
            ctx.checkpoints.write_artifact("review.json", state.final_review)
            ctx.checkpoints.write_artifact("review.md", render_review_markdown(state))
            if self.config.generate_html_report:
                ctx.checkpoints.write_artifact("review.html", render_html(state.to_dict()))
            if self.config.generate_csv_exports:
                csv_path = run_dir / "artifacts" / "major_concerns.csv"
                export_concerns_csv(state.admitted_concerns, csv_path)
        else:
            ctx.checkpoints.write_artifact("FAILED_VALIDATION.json", {"status":"failed_validation","final_review_exportable":False,"hard_invariant_failures":state.hard_invariant_failures})
        def _prompt_sha(name: str) -> str:
            text = ctx.prompts.core(name)
            return hashlib.sha256(text.encode("utf-8")).hexdigest()

        core_prompt_name = "CORE_REVIEWER_PROMPT.md" if self.config.pipeline == "core" and self.config.review_mode == "initial" else "PEER_REVIEW_PROMPT.md"
        verifier_prompt_name = "CORE_VERIFIER_PROMPT.md" if self.config.pipeline == "core" and self.config.review_mode == "initial" else "INDEPENDENT_VERIFIER_PROMPT.md"
        run_manifest = {
            "run_id": state.run_id,
            "review_mode": self.config.review_mode,
            "depth_mode": self.config.mode,
            "pipeline": self.config.pipeline,
            "runtime_identity": "Beihang Referee Core Review Pipeline" if self.config.pipeline == "core" and self.config.review_mode == "initial" else "Beihang Referee Full Audit/Mode Pipeline",
            "models": {
                "review_model": self.config.model,
                "strategic_model": self.config.strategic_model or self.config.model,
                "verifier_model": self.config.verifier_model or self.config.model,
                "verifier_independence": "cross-model" if (self.config.verifier_model and (self.config.verifier_model != (self.config.strategic_model or self.config.model))) else "fresh-context/same-model",
            },
            "calibration_inputs": {
                "target_journal": self.config.target_journal,
                "journal_profile": self.config.journal_profile,
                "benchmark_profile": self.config.benchmark_profile,
            },
            "state_sha256": stable_json_hash(state.to_dict()),
            "core_peer_review_prompt_sha256": _prompt_sha(core_prompt_name),
            "independent_verifier_prompt_sha256": _prompt_sha(verifier_prompt_name),
            "input_files": json.loads((run_dir / "inputs.json").read_text(encoding="utf-8")),
            "stage_count": len(state.stage_records),
            "status": state.status,
            "final_review_exportable": state.final_review_exportable,
            "hard_invariant_failures": state.hard_invariant_failures,
            "soft_invariant_failures": state.soft_invariant_failures,
        }
        ctx.checkpoints.write_artifact("run_manifest.json", run_manifest)
        registry.upsert(
            state.run_id, status=state.status, review_mode=self.config.review_mode, depth_mode=self.config.mode,
            query=state.query, input_count=len(state.manuscript_paths),
            summary={
                "admitted_major_comments": len(state.admitted_concerns),
                "rejected_major_comments": len(state.rejected_concerns),
                "warnings": len(state.warnings),
                "specialists": len(state.specialist_results),
            },
        )
        return state
