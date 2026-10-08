from __future__ import annotations
import argparse
import asyncio
import json
import os
from pathlib import Path

from .config import ReviewConfig
from .engine import ReviewEngine
from .providers.scripted import ScriptedLLMProvider, ScriptedSearchProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .providers.scholarly_search import FederatedScholarlySearchProvider
from .ingestion import PackageInspector
from .comparison import revision_diff, audit_rebuttal_structure
from .documents import DocumentLoader
from .modes import ReviewModeRegistry
from .scholarly import ScholarlyRegistry
from .evals import evaluate_cases
from .profiles import ProfileRegistry
from .lifecycle import RunRegistry, ReviewWorkspace
from .finalization import freeze_run, verify_handoff
from .version import __version__


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="referee", description="Beihang Referee — evidence-grounded agentic peer review for scientific manuscripts")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("review", help="Run the full evidence-locked manuscript review pipeline")
    r.add_argument("paths", nargs="+", help="Manuscript/supplement/data/code files")
    r.add_argument("--query", default="Scientific peer review")
    r.add_argument("--profile", choices=ProfileRegistry().names(), help="Named configuration profile")
    r.add_argument("--mode", choices=["standard", "deep", "exhaustive"], help="Review depth")
    r.add_argument("--pipeline", choices=["core", "full"], help="Scientific review pipeline; default is the core pipeline unless a named profile overrides it")
    r.add_argument("--review-mode", choices=ReviewModeRegistry().names(), help="Purpose of the review")
    r.add_argument("--run-root", default="runs")
    r.add_argument("--run-id")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--provider", choices=["openai-compatible", "scripted"], default="openai-compatible")
    r.add_argument("--model", default=os.getenv("REFEREE_MODEL"), help="Model identifier; can also be set with REFEREE_MODEL")
    r.add_argument("--strategic-model", default=os.getenv("REFEREE_STRATEGIC_MODEL"), help="Optional model for core/scorecard/calibration reasoning")
    r.add_argument("--verifier-model", default=os.getenv("REFEREE_VERIFIER_MODEL"), help="Optional distinct model for independent verification")
    r.add_argument("--scripted-responses", help="JSON fixture for offline deterministic runs")
    r.add_argument("--search-backend", choices=["federated", "none", "scripted"], help="Scholarly search backend; default comes from the profile/config")
    r.add_argument("--scholarly-providers", default="crossref,openalex,semantic_scholar,pubmed,arxiv,europe_pmc", help="Comma-separated scholarly providers for federated search")
    r.add_argument("--prior-manuscript", help="Required for revision mode unless supplied programmatically")
    r.add_argument("--prior-concerns", help="Optional JSON/JSONL prior concern set for revision closure auditing")
    r.add_argument("--reviewer-comments", help="Reviewer comments for rebuttal/meta-review modes")
    r.add_argument("--rebuttal", help="Author rebuttal/response file for rebuttal mode")
    r.add_argument("--scorecard", action="store_true", help="Add the diagnostic 50-dimension scorecard after the scientific review is frozen")
    r.add_argument("--target-journal", help="Calibrate venue fit for one named journal after scientific judgments are frozen")
    r.add_argument("--journal-profile", help="JSON profile built from current official journal pages; makes venue calibration evidence-grounded")
    r.add_argument("--benchmark-profile", help="Built-in benchmark profile name or JSON path for post-scorecard reference comparison")

    val = sub.add_parser("validate", help="Run Referee's reproducible validation campaign")
    val.add_argument("--suite", choices=["integrity","full"], default="integrity")
    val.add_argument("--output", default="validation-results")
    val.add_argument("--model", default=os.getenv("REFEREE_MODEL"), help="Review model for full validation")
    val.add_argument("--verifier-model", default=os.getenv("REFEREE_VERIFIER_MODEL"))
    val.add_argument("--judge-model-a", default=os.getenv("REFEREE_JUDGE_MODEL_A"))
    val.add_argument("--judge-model-b", default=os.getenv("REFEREE_JUDGE_MODEL_B"))
    val.add_argument("--adjudicator-model", default=os.getenv("REFEREE_ADJUDICATOR_MODEL"))
    val.add_argument("--search-backend", choices=["federated","none"], default="federated")
    val.add_argument("--scholarly-providers", default="crossref,openalex,semantic_scholar,pubmed,arxiv,europe_pmc")
    val.add_argument("--repeats", type=int, default=3)
    val.add_argument("--limit-per-corpus", type=int, help="Development smoke-test only; omit for the official full campaign")
    val.add_argument("--skip-source-tests", action="store_true", help="Use only when tests are unavailable in an installed wheel")
    val.add_argument("--require-independent-evaluation", action="store_true", help="Require cross-model evaluator independence for an external validation claim")

    v = sub.add_parser("validate-run", help="Validate a completed run's state invariants")
    v.add_argument("run_dir")

    i = sub.add_parser("inspect-package", help="Inspect manuscript/reproducibility package structure without an LLM")
    i.add_argument("paths", nargs="+")
    i.add_argument("--json-out")

    c = sub.add_parser("compare-revision", help="Diff two manuscript versions")
    c.add_argument("old")
    c.add_argument("new")
    c.add_argument("--json-out")

    b = sub.add_parser("audit-rebuttal", help="Check reviewer-response traceability signals")
    b.add_argument("response_file")

    e = sub.add_parser("benchmark", help="Run deterministic evidence-lock benchmark cases")
    e.add_argument("cases")

    s = sub.add_parser("serve", help="Serve review runs over the optional local workbench")
    s.add_argument("--run-root", default="runs")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)

    lr = sub.add_parser("list-runs", help="List locally indexed review runs")
    lr.add_argument("--run-root", default="runs")
    lr.add_argument("--limit", type=int, default=100)

    ri = sub.add_parser("rebuild-run-index", help="Rebuild the local run registry from run directories")
    ri.add_argument("--run-root", default="runs")

    fr = sub.add_parser("finalize-run", help="Freeze a completed run into a checksum-verifiable handoff bundle")
    fr.add_argument("run_dir")

    vh = sub.add_parser("verify-handoff", help="Verify all file hashes inside a frozen handoff bundle")
    vh.add_argument("bundle")

    note = sub.add_parser("add-note", help="Attach a human note to a run without changing model-generated state")
    note.add_argument("run_dir")
    note.add_argument("text")
    note.add_argument("--author", default="reviewer")

    cs = sub.add_parser("set-concern-status", help="Set the human workflow status of an admitted concern")
    cs.add_argument("run_dir")
    cs.add_argument("concern_id")
    cs.add_argument("status", choices=["open", "resolved", "deferred", "not_actionable", "accepted_risk"])
    cs.add_argument("--note", default="")

    sub.add_parser("list-modes", help="List supported review purposes")
    sub.add_parser("list-profiles", help="List built-in configuration profiles")
    sub.add_parser("list-scholarly-providers", help="List built-in scholarly search adapters")
    return p


def _config_from_args(args) -> ReviewConfig:
    overrides = {
        "run_root": args.run_root,
        "model": args.model,
        "mode": args.mode,
        "pipeline": args.pipeline,
        "review_mode": args.review_mode,
        "search_backend": args.search_backend,
        "target_journal": getattr(args, "target_journal", None),
        "journal_profile": getattr(args, "journal_profile", None),
        "benchmark_profile": getattr(args, "benchmark_profile", None),
        "strategic_model": getattr(args, "strategic_model", None),
        "verifier_model": getattr(args, "verifier_model", None),
    }
    if args.profile:
        cfg = ReviewConfig.from_profile(args.profile, **overrides)
        cfg.enable_scorecard = bool(getattr(args, "scorecard", False) or getattr(args, "benchmark_profile", None))
        if cfg.benchmark_profile and not cfg.target_journal:
            from .benchmarking import load_benchmark_profile
            profile = load_benchmark_profile(cfg.benchmark_profile)
            if profile and profile.get("journal"):
                cfg.target_journal = str(profile["journal"])
        return cfg
    cfg = ReviewConfig(
        mode=args.mode or "deep",
        pipeline=args.pipeline or "lean",
        review_mode=args.review_mode or "initial",
        run_root=args.run_root,
        model=args.model,
        target_journal=getattr(args, "target_journal", None),
        journal_profile=getattr(args, "journal_profile", None),
        benchmark_profile=getattr(args, "benchmark_profile", None),
        strategic_model=getattr(args, "strategic_model", None),
        verifier_model=getattr(args, "verifier_model", None),
    )
    cfg.enable_scorecard = bool(getattr(args, "scorecard", False) or getattr(args, "benchmark_profile", None))
    if cfg.benchmark_profile and not cfg.target_journal:
        from .benchmarking import load_benchmark_profile
        profile = load_benchmark_profile(cfg.benchmark_profile)
        if profile and profile.get("journal"):
            cfg.target_journal = str(profile["journal"])
    return cfg


async def _run(args) -> int:
    cfg = _config_from_args(args)
    if args.provider == "scripted":
        responses = {}
        if args.scripted_responses:
            responses = json.loads(Path(args.scripted_responses).read_text(encoding="utf-8"))
        llm = ScriptedLLMProvider(responses)
        search = ScriptedSearchProvider()
    else:
        selected_model = args.model or os.getenv("REFEREE_MODEL")
        if not selected_model:
            raise SystemExit("Pass --model or set REFEREE_MODEL when using the openai-compatible provider.")
        cfg.model = selected_model
        llm = OpenAICompatibleProvider(default_model=selected_model)
        backend = args.search_backend or cfg.search_backend
        if cfg.enable_literature_search and backend == "federated":
            names = [x.strip() for x in args.scholarly_providers.split(",") if x.strip()]
            search = FederatedScholarlySearchProvider(names, max_concurrency=cfg.max_concurrency)
        elif backend == "none":
            search = None
        elif backend == "scripted":
            search = ScriptedSearchProvider()
        else:
            raise SystemExit(f"Unsupported search backend: {backend}. Use --search-backend none to explicitly disable literature retrieval.")
    engine = ReviewEngine(llm=llm, search=search, config=cfg)
    mode_inputs = {k: v for k, v in {
        "prior_manuscript": args.prior_manuscript, "prior_concerns": args.prior_concerns,
        "reviewer_comments": args.reviewer_comments, "rebuttal": args.rebuttal,
    }.items() if v}
    state = await engine.review(args.paths, query=args.query, run_id=args.run_id, resume=args.resume, mode_inputs=mode_inputs)
    print(Path(cfg.run_root) / state.run_id / "artifacts" / "review.md")
    return 0


def _write_or_print(obj, out=None):
    text = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(out)
    else:
        print(text)


def main() -> int:
    args = parser().parse_args()
    if args.command == "review":
        return asyncio.run(_run(args))
    if args.command == "validate":
        from .validation.campaign import run_validation_campaign
        providers=[x.strip() for x in args.scholarly_providers.split(",") if x.strip()]
        result=asyncio.run(run_validation_campaign(suite=args.suite,output_dir=args.output,review_model=args.model,verifier_model=args.verifier_model,judge_model_a=args.judge_model_a,judge_model_b=args.judge_model_b,adjudicator_model=args.adjudicator_model,search_backend=args.search_backend,scholarly_providers=providers,repeats=max(1,args.repeats),limit_per_corpus=args.limit_per_corpus,skip_source_tests=args.skip_source_tests,require_external_independence=args.require_independent_evaluation))
        _write_or_print(result)
        return 0 if result.get("status")=="completed" else 1
    if args.command == "validate-run":
        from .validation import validate_state_consistency
        data = json.loads((Path(args.run_dir) / "state.json").read_text(encoding="utf-8"))
        errors = validate_state_consistency(data)
        if errors:
            print("\n".join(errors)); return 1
        print("OK"); return 0
    if args.command == "inspect-package":
        _write_or_print(PackageInspector().inspect(args.paths).to_dict(), args.json_out); return 0
    if args.command == "compare-revision":
        loader = DocumentLoader(); old = loader.load(args.old).text; new = loader.load(args.new).text
        _write_or_print(revision_diff(old, new), args.json_out); return 0
    if args.command == "audit-rebuttal":
        text = DocumentLoader().load(args.response_file).text
        _write_or_print(audit_rebuttal_structure(text)); return 0
    if args.command == "benchmark":
        result = evaluate_cases(args.cases); _write_or_print(result); return 0 if result["passed"] == result["total"] else 1
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:
            raise SystemExit("Server support requires: pip install .[server]") from exc
        from .server import create_app
        uvicorn.run(create_app(args.run_root), host=args.host, port=args.port); return 0
    if args.command == "list-runs":
        reg = RunRegistry(args.run_root)
        if not reg.list(limit=1):
            reg.rebuild()
        _write_or_print(reg.list(limit=args.limit)); return 0
    if args.command == "rebuild-run-index":
        print(RunRegistry(args.run_root).rebuild()); return 0
    if args.command == "finalize-run":
        _write_or_print(freeze_run(args.run_dir)); return 0
    if args.command == "verify-handoff":
        result = verify_handoff(args.bundle); _write_or_print(result); return 0 if result["valid"] else 1
    if args.command == "add-note":
        _write_or_print(ReviewWorkspace(args.run_dir).add_note(args.text, author=args.author)); return 0
    if args.command == "set-concern-status":
        _write_or_print(ReviewWorkspace(args.run_dir).set_concern_status(args.concern_id, args.status, note=args.note)); return 0
    if args.command == "list-modes":
        reg = ReviewModeRegistry()
        for name in reg.names():
            spec = reg.get(name); print(f"{name}\t{spec.description}")
        return 0
    if args.command == "list-profiles":
        for name in ProfileRegistry().names(): print(name)
        return 0
    if args.command == "list-scholarly-providers":
        for name in ScholarlyRegistry().names(): print(name)
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
