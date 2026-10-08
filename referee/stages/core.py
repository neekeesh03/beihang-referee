from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from .base import Stage
from ..documents import DocumentLoader, scan_prompt_injection
from ..models import ReviewState
from ..providers.base import LLMRequest
from ..context_manager import ContextManager
from ..validation import validate_major_comment
from ..validation.identifiers import (
    append_evidence_anchors, canonicalize_core_claims, claim_alias_map,
    remap_concern_references, allocate_concern_id, assert_unique_ids, anchor_alias_map,
)
from ..contracts import schemas as S
from ..contracts import validate_json_contract, normalize_concern, Concern, validate_and_materialize_core_review
from ..utils.hashing import stable_json_hash
from ..verification import verify_anchor_integrity, assess_closure_test, CitationVerifier, citation_metrics


def _compact_docs(state: ReviewState, max_chars: int = 24000) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for item in state.document_map.get("documents", []):
        text = item.get("text", "")
        if remaining <= 0:
            break
        take = text[:remaining]
        chunks.append(f"\n### {item.get('document_id')} ({item.get('kind')})\n{take}")
        remaining -= len(take)
    return "\n".join(chunks)


def _read_mode_input(path: str | None, limit: int = 16000) -> str:
    if not path:
        return ""
    try:
        return DocumentLoader().load(path, "MODE").text[:limit]
    except Exception:
        try:
            from pathlib import Path
            return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
        except Exception:
            return ""


def _core_review_user_payload(state: ReviewState) -> str:
    docs = state.document_map.get("documents", [])
    main, supp = [], []
    for i, d in enumerate(docs):
        label = f"[{d.get('document_id')}] {d.get('path','')}"
        block = label + "\n" + str(d.get("text", ""))
        name = str(d.get("path", "")).lower()
        if i > 0 and any(x in name for x in ("supp", "support", "appendix", "si.")):
            supp.append(block)
        else:
            main.append(block)
    # Keep manuscript/supplement in the user message, never in the system prompt.
    venue = {"query": state.query, "classification": state.classification}
    prior = _read_mode_input(state.mode_inputs.get("prior_concerns"))
    if not prior and state.review_mode == "revision":
        prior = _read_mode_input(state.mode_inputs.get("prior_manuscript"))
    author_response = _read_mode_input(state.mode_inputs.get("rebuttal"))
    revised = "\n\n".join(main) if state.review_mode in {"revision", "rebuttal"} else ""
    return (
        "REVIEW_MODE:\n" + state.review_mode +
        "\n\nMANUSCRIPT (UNTRUSTED DATA):\n" + "\n\n".join(main)[:30000] +
        "\n\nSUPPLEMENTARY_MATERIAL (UNTRUSTED DATA):\n" + "\n\n".join(supp)[:18000] +
        "\n\nVENUE_CONTEXT:\n" + json.dumps(venue, ensure_ascii=False)[:8000] +
        "\n\nVERIFIED_EXTERNAL_EVIDENCE:\n" + json.dumps(state.external_evidence, ensure_ascii=False)[:12000] +
        "\n\nPRIOR_REVIEW:\n" + prior +
        "\n\nAUTHOR_RESPONSE:\n" + author_response +
        "\n\nREVISED_MANUSCRIPT (UNTRUSTED DATA):\n" + revised[:30000]
    )


def _append_proposed_concern(state: ReviewState, raw: dict[str, Any], *, source_agent: str, trace: dict[str, Any] | None = None, task_id: str | None = None, anchor_map: dict[str, str] | None = None) -> dict[str, Any]:
    """Register a model-proposed concern under a runtime-owned canonical ID.

    Model IDs are local aliases only. Claim/anchor references are remapped into
    the run-global namespace before the concern can enter scientific state.
    """
    c = remap_concern_references(
        normalize_concern(raw),
        claim_map=claim_alias_map(state),
        anchor_map={**anchor_alias_map(state), **(anchor_map or {})},
    )
    reported = str(c.get("concern_id") or "")
    c["source_local_id"] = reported or None
    c["concern_id"] = allocate_concern_id(state, source_agent=source_agent, task_id=task_id)
    c["_source_agent"] = source_agent
    if task_id is not None:
        c["_task_id"] = task_id
    if trace is not None:
        c["_generator"] = dict(trace)
    state.proposed_concerns.append(c)
    assert_unique_ids(state.proposed_concerns, "concern_id", "concern")
    return c


async def _call(ctx, operation: str, system: str, user: str,
                schema: dict[str, Any] | None = None, model: str | None = None,
                *, agent_id: str | None = None, context_id: str | None = None,
                trace_out: dict[str, Any] | None = None) -> Any:
    """Call an LLM through a fresh, explicitly identified context.

    Scientific stages pass schemas here; strict mode validates the returned
    object locally as well as requesting provider-side structured output.
    """
    ctx.budget.consume_llm()
    request_id = uuid.uuid4().hex
    context_id = context_id or f"ctx-{uuid.uuid4().hex}"
    agent_id = agent_id or f"agent-{operation}"
    selected_model = model or ctx.config.model
    result = await ctx.llm.complete(
        LLMRequest(
            operation=operation,
            system=system,
            user=user,
            schema=schema,
            model=selected_model,
            temperature=0.0,
            request_id=request_id,
            context_id=context_id,
            agent_id=agent_id,
        )
    )
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            result = {"text": result}
    result = result or {}
    if schema is not None and ctx.config.strict_schema:
        errors = validate_json_contract(result, schema)
        if errors:
            raise ValueError(f"Structured output violation for {operation}: " + "; ".join(errors[:8]))
    if trace_out is not None:
        trace_out.update({
            "request_id": request_id, "context_id": context_id, "agent_id": agent_id,
            "operation": operation, "model": selected_model,
        })
    return result


class IntakeStage(Stage):
    stage_id = "01_intake"

    async def run(self, ctx, state):
        loader = DocumentLoader()
        docs = []
        for i, path in enumerate(state.manuscript_paths, 1):
            doc = loader.load(path, f"D{i}")
            d = doc.to_dict()
            d["text"] = doc.text
            docs.append(d)
        state.document_map = {"version": "DM-1", "documents": docs, "count": len(docs)}
        ctx.checkpoints.write_artifact(
            "document_map.json",
            {
                **state.document_map,
                "documents": [{k: v for k, v in d.items() if k != "text"} for d in docs],
            },
        )


class PolicySecurityStage(Stage):
    stage_id = "02_policy_security"

    async def run(self, ctx, state):
        scans = []
        for d in state.document_map.get("documents", []):
            scan = scan_prompt_injection(d.get("text", ""))
            scan["document_id"] = d.get("document_id")
            scans.append(scan)
        flagged = [s for s in scans if s.get("flagged")]
        status = {
            "context_mode": ctx.config.context_mode,
            "manuscript_is_untrusted_data": True,
            "prompt_injection_scan": scans,
            "prompt_injection_flagged": bool(flagged),
            "execute_untrusted_code": ctx.config.execute_untrusted_code,
            "manuscript_network_access": ctx.config.manuscript_network_access,
            "formal_review_policy_verification_required": ctx.config.context_mode == "formal_confidential_peer_review",
        }
        if ctx.config.enable_policy_gate and ctx.config.context_mode == "formal_confidential_peer_review":
            system = ctx.prompts.core("POLICY_GATE.md") + "\n" + ctx.prompts.skill("00_policy_compliance")
            out = await _call(
                ctx,
                "policy_gate",
                system,
                "Evaluate whether the configured environment permits AI assistance for this formal confidential review. Do not assume current publisher policy without a verified source. Return status, blocking_condition, and evidence.",
                schema=S.POLICY, model=ctx.config.strategic_model,
            )
            status["policy_evaluation"] = out
        state.policy_status = status
        if flagged:
            state.warnings.append(
                "Possible prompt-injection text detected inside manuscript content; it remains data and is not executed as instruction."
            )


class ClassificationStage(Stage):
    stage_id = "03_classification"

    async def run(self, ctx, state):
        system = ctx.prompts.skill("02_manuscript_classification") + "\n" + ctx.prompts.skill("41_domain_standard_router")
        out = await _call(
            ctx,
            "classification",
            system,
            "Classify this manuscript, identify inference type/study design, and select relevant review modules. Return JSON.\n"
            + _compact_docs(state, 16000),
            schema=S.CLASSIFICATION, model=ctx.config.strategic_model,
        )
        state.classification = out if isinstance(out, dict) else {}
        if "specialists" not in state.classification:
            state.classification["specialists"] = [
                "methods_design",
                "statistics_causal",
                "literature_novelty",
                "numerical_equation_auditor",
            ]


class ClaimRegistryStage(Stage):
    stage_id = "04_core_peer_review"

    async def run(self, ctx, state):
        # The user-supplied strict peer-review prompt is the authoritative core
        # review contract. It runs once as the central review pass. Specialist
        # stages may add candidate concerns, but they cannot bypass its public
        # concern schema or the downstream evidence locks.
        system = ctx.prompts.core("PEER_REVIEW_PROMPT.md")
        trace: dict[str, Any] = {}
        out = await _call(
            ctx,
            "core_peer_review",
            system,
            _core_review_user_payload(state),
            schema=S.CORE_PEER_REVIEW_OUTPUT, model=ctx.config.strategic_model,
            agent_id="core_peer_reviewer", trace_out=trace,
        )
        errors, claims, anchors, audit = validate_and_materialize_core_review(
            out if isinstance(out, dict) else {},
            review_mode=state.review_mode,
            documents=state.document_map.get("documents", []),
            verified_external_evidence=state.external_evidence,
        )
        state.core_review = out if isinstance(out, dict) else {}
        audit["core_prompt_sha256"] = __import__("hashlib").sha256(system.encode("utf-8")).hexdigest()
        audit["model_verification_fields_trusted_as_proof"] = False
        state.core_review_validation = audit
        ctx.checkpoints.write_artifact("core_peer_review.json", state.core_review)
        ctx.checkpoints.write_artifact("core_peer_review_validation.json", audit)
        if errors and ctx.config.strict_schema:
            raise ValueError("Core peer-review deterministic validation failed: " + "; ".join(errors[:12]))
        # Convert prompt-local C001/A001 identifiers into runtime-owned global
        # identifiers. Prompt-local identifiers remain audit metadata only.
        state.claims = []
        state.evidence_anchors = []
        anchor_map = append_evidence_anchors(state, anchors, source_stage="CORE", reviewer_id="core")
        claim_map = canonicalize_core_claims(state, claims, anchor_map=anchor_map)
        # Remap anchor supports metadata after claims have canonical IDs.
        for a in state.evidence_anchors:
            supports = [claim_map.get(x, x) for x in str(a.get("supports") or "").split(",") if x]
            a["supports"] = ",".join(supports)
        for c in state.core_review.get("major_concerns", []):
            if not isinstance(c, dict):
                continue
            _append_proposed_concern(state, c, source_agent="core_peer_review", trace=trace, anchor_map=anchor_map)
        audit["runtime_claim_id_map"] = claim_map
        audit["runtime_anchor_id_map"] = anchor_map



AVAILABLE_TASK_SKILLS = {
    "literature_novelty": ["04_reference_forensics", "05_literature_search", "07_novelty", "08_research_gap"],
    "theory_construct": ["09_construct_theory", "10_rival_theory_falsifiability"],
    "methods_design": ["11_empirical_design", "12_sampling_measurement"],
    "statistics_causal": ["13_causal_inference", "14_statistics"],
    "benchmark_model": ["15_benchmark_epistemology", "16_model_validation", "17_ml_ai"],
    "simulation": ["18_computational_simulation"],
    "systematic_review_meta": ["19_systematic_review_meta"],
    "qualitative": ["20_qualitative"],
    "rct_intervention": ["21_rct_intervention"],
    "observational_epidemiology": ["22_observational_epidemiology"],
    "diagnostic_prognostic": ["23_diagnostic_prognostic"],
    "measurement_instrument": ["24_measurement_instrument"],
    "figures_tables": ["25_figures_tables"],
    "code_reproducibility": ["26_code_reproducibility"],
    "robustness_generalization": ["27_robustness_generalization"],
    "ethics_integrity": ["28_ethics_integrity", "37_retraction_citation_integrity"],
    "reporting_guidelines": ["29_reporting_guidelines"],
    "numerical_equation_auditor": ["38_equations_units_numerical_consistency"],
    "review_bias_fairness": ["42_review_bias_fairness"],
    "electrochemistry_fuel_cells": ["44_electrochemistry_fuel_cells", "46_environmental_water_processes", "48_analytical_chemistry_measurement", "52_experimental_metrology_uncertainty"],
    "materials_characterization": ["45_materials_characterization", "48_analytical_chemistry_measurement", "54_spectroscopy_microscopy"],
    "environmental_process": ["46_environmental_water_processes", "49_energy_lca_tea", "53_chemical_kinetics_transport", "55_scaleup_process_engineering"],
    "microbiology_omics": ["47_microbiology_biofilms_omics"],
    "energy_lca_tea": ["49_energy_lca_tea", "55_scaleup_process_engineering"],
    "computational_science": ["50_computational_science_numerics", "53_chemical_kinetics_transport"],
    "ml_science": ["51_ml_for_science"],
    "metrology_measurement": ["48_analytical_chemistry_measurement", "52_experimental_metrology_uncertainty"],
}

AGENT_FILE_MAP = {
    "literature_novelty": "02_literature_novelty.md",
    "theory_construct": "03_theory_construct.md",
    "methods_design": "04_methods_design.md",
    "statistics_causal": "05_statistics_causal.md",
    "benchmark_model": "06_benchmark_model.md",
    "code_reproducibility": "07_code_reproducibility.md",
    "ethics_integrity": "08_ethics_integrity.md",
    "numerical_equation_auditor": "14_numerical_equation_auditor.md",
    "electrochemistry_fuel_cells": "16_electrochemistry_reviewer.md",
    "materials_characterization": "17_materials_characterization_reviewer.md",
    "environmental_process": "18_environmental_process_reviewer.md",
    "microbiology_omics": "19_microbiology_omics_reviewer.md",
    "energy_lca_tea": "20_energy_lca_tea_reviewer.md",
    "computational_science": "21_computational_science_reviewer.md",
    "ml_science": "22_ml_science_reviewer.md",
    "metrology_measurement": "23_metrology_measurement_reviewer.md",
}


class ReviewPlanStage(Stage):
    stage_id = "05_review_plan"

    async def run(self, ctx, state):
        system = ctx.prompts.agent("00_orchestrator.md") + "\n" + ctx.prompts.skill("41_domain_standard_router")
        out = await _call(
            ctx,
            "review_plan",
            system,
            "Create a claim-centered review plan. Return {tasks:[{task_id,specialist,claim_ids,objective,priority,evidence_needs}]}. "
            "Use only specialist names from this allowlist: " + ", ".join(AVAILABLE_TASK_SKILLS) + ".\n"
            "Classification:\n" + json.dumps(state.classification, ensure_ascii=False)[:10000] +
            "\nClaims:\n" + json.dumps(state.claims, ensure_ascii=False)[:12000],
            schema=S.REVIEW_PLAN, model=ctx.config.strategic_model,
        )
        tasks = out.get("tasks", []) if isinstance(out, dict) else []
        valid = []
        for i, task in enumerate(tasks, 1):
            if not isinstance(task, dict) or task.get("specialist") not in AVAILABLE_TASK_SKILLS:
                continue
            task.setdefault("task_id", f"T{i:03d}")
            task.setdefault("claim_ids", [])
            task.setdefault("priority", "medium")
            valid.append(task)
        if not valid:
            from ..reviewers.router import route_reviewers
            requested = route_reviewers(state.classification, state.claims, limit=ctx.config.specialist_limit) or ["methods_design", "statistics_causal"]
            valid = [
                {
                    "task_id": f"T{i:03d}",
                    "specialist": s,
                    "claim_ids": [c.get("claim_id") for c in state.claims if c.get("claim_id")][:8],
                    "objective": f"Audit relevant claims from the {s} perspective",
                    "priority": "high" if i <= 2 else "medium",
                    "evidence_needs": [],
                }
                for i, s in enumerate(requested, 1)
                if s in AVAILABLE_TASK_SKILLS
            ]
        # Deduplicate by specialist + claim cluster while preserving order.
        seen = set(); deduped = []
        for task in valid:
            key = (task["specialist"], tuple(sorted(task.get("claim_ids") or [])))
            if key not in seen:
                seen.add(key); deduped.append(task)
        state.review_plan = deduped[: ctx.config.specialist_limit]
        ctx.checkpoints.write_artifact("review_plan.json", state.review_plan)


class NumericalStage(Stage):
    stage_id = "06_numerical_ledger"

    async def run(self, ctx, state):
        system = ctx.prompts.skill("38_equations_units_numerical_consistency")
        trace: dict[str, Any] = {}
        out = await _call(
            ctx,
            "numerical_ledger",
            system,
            "Audit equations, units, denominators, sample sizes and repeated numerical facts across files. Return {items:[], concerns:[], evidence_anchors:[]}. Every major concern must satisfy the canonical Referee major-concern schema.\n"
            + _compact_docs(state, 24000),
            schema=S.NUMERICAL, agent_id="numerical_equation_auditor", trace_out=trace,
        )
        state.numerical_ledger = out.get("items", []) if isinstance(out, dict) else []
        anchor_map = append_evidence_anchors(
            state, out.get("evidence_anchors", []) if isinstance(out, dict) else [],
            source_stage="NUMERICAL", reviewer_id="numerical_equation_auditor",
        )
        for c in out.get("concerns", []) if isinstance(out, dict) else []:
            _append_proposed_concern(state, c, source_agent="numerical_equation_auditor", trace=trace, anchor_map=anchor_map)


async def _enrich_search_result(provider, result: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    if any(enriched.get(k) for k in ("raw_content", "content", "text")):
        enriched["content_status"] = "provided_by_retriever"
        return enriched
    url = enriched.get("url") or enriched.get("href")
    if url and provider:
        try:
            fetched = await provider.fetch(url)
            if isinstance(fetched, dict):
                enriched.update({"fetched": fetched, "content_status": "fetched"})
        except (NotImplementedError, Exception) as exc:
            enriched["content_status"] = "not_fetched"
            enriched["fetch_error"] = type(exc).__name__
    return enriched


def _opened_content(result: dict[str, Any]) -> str:
    return str(
        result.get("raw_content") or result.get("content") or result.get("text")
        or (result.get("fetched") or {}).get("raw_content")
        or (result.get("fetched") or {}).get("content") or ""
    )


def _norm_key(value: Any) -> str:
    import re
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _materialize_literature_anchors(anchors: list[dict[str, Any]], ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bind model-proposed external anchors to actually opened search results.

    Model-written content status/hash values are retained only as ignored audit
    metadata. Runtime hashes are recomputed from the fetched/opened content.
    """
    import hashlib
    rows=[r for q in ledger for r in (q.get("results") or []) if isinstance(r,dict)]
    materialized=[]
    for raw in anchors:
        a=dict(raw)
        if str(a.get("source_type") or "").lower() not in {"external", "literature"}:
            materialized.append(a); continue
        model_status=a.get("content_status"); model_hash=a.get("content_sha256")
        candidates=[]
        keys={_norm_key(a.get("url")),_norm_key(a.get("document_id")),_norm_key(a.get("locator"))}
        keys.discard("")
        fact=_norm_key(a.get("quote_or_fact"))
        for r in rows:
            rkeys={_norm_key(r.get("url")),_norm_key(r.get("doi")),_norm_key(r.get("title"))}
            for v in (r.get("identifiers") or {}).values() if isinstance(r.get("identifiers"),dict) else []:
                rkeys.add(_norm_key(v))
            content=_opened_content(r)
            if keys & rkeys or (fact and content and fact in _norm_key(content)):
                candidates.append((r,content))
        chosen=None
        # Prefer candidates whose opened content contains the exact normalized fact.
        exact=[x for x in candidates if fact and x[1] and fact in _norm_key(x[1])]
        if exact: chosen=exact[0]
        elif len(candidates)==1: chosen=candidates[0]
        if chosen:
            r,content=chosen
            a["url"]=r.get("url") or a.get("url")
            a["document_id"]=str(r.get("doi") or r.get("url") or r.get("title") or a.get("document_id") or "external")
            a["content_status"]="opened" if content else "not_opened"
            a["content_sha256"]=hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None
            if content: a["raw_content"]=content
            a["_matched_provider"]=r.get("provider")
            a["_matched_title"]=r.get("title")
            a["_matched_source_record"]={k:r.get(k) for k in ("title","year","doi","url","authors","venue","provider","identifiers","raw_content","content","text","fetched") if r.get(k) is not None}
        else:
            a["content_status"]="not_opened"
            a["content_sha256"]=None
        a["_model_content_status_ignored"]=model_status
        a["_model_content_sha256_ignored"]=model_hash
        materialized.append(a)
    return materialized


class LiteratureStage(Stage):
    stage_id = "07_literature"

    async def run(self, ctx, state):
        if not ctx.config.enable_literature_search:
            state.literature_status = {"status": "disabled", "novelty_assessment_status": "insufficient_external_evidence"}
            return
        system = ctx.prompts.skill("05_literature_search") + "\n" + ctx.prompts.skill("39_literature_search_provenance")
        plan = await _call(
            ctx,
            "literature_plan",
            system,
            "Generate a bounded, reproducible query plan for novelty and pivotal claims. Return {queries:[{query,goal,claim_ids}]}.\nClaims:\n"
            + json.dumps(state.claims, ensure_ascii=False)[:16000],
            schema=S.LITERATURE_PLAN,
        )
        queries = (plan.get("queries", []) if isinstance(plan, dict) else [])[: ctx.config.literature_query_budget]
        ledger = []
        if ctx.search:
            sem = asyncio.Semaphore(ctx.config.max_concurrency)

            async def one(q):
                async with sem:
                    ctx.budget.consume_search()
                    raw = await ctx.search.search(q.get("query", ""), limit=8)
                    enriched = await asyncio.gather(*(_enrich_search_result(ctx.search, r) for r in raw[:8]))
                    return {**q, "results": enriched}

            ledger = await asyncio.gather(*(one(q) for q in queries if q.get("query")))
        else:
            ledger = [{**q, "results": [], "status": "search-provider-unavailable"} for q in queries]
        state.search_ledger = ledger
        opened = sum(1 for row in ledger for r in row.get("results", []) if r.get("content_status") in {"fetched", "provided_by_retriever", "opened"})
        total_results = sum(len(row.get("results", [])) for row in ledger)
        if ctx.search and opened > 0:
            state.literature_status = {"status": "available", "queries": len(queries), "results": total_results, "opened_sources": opened}
        elif ctx.search:
            state.literature_status = {"status": "insufficient", "queries": len(queries), "results": total_results, "opened_sources": opened, "novelty_assessment_status": "insufficient_external_evidence"}
        else:
            state.literature_status = {"status": "unavailable", "queries": len(queries), "results": 0, "opened_sources": 0, "novelty_assessment_status": "insufficient_external_evidence"}
            state.warnings.append("Literature search was enabled but no search provider was available; novelty-related decisive claims fail closed.")
        lit_trace: dict[str, Any] = {}
        synthesis = await _call(
            ctx,
            "literature_synthesis",
            system,
            "Assess nearest prior art, contradictory/null evidence, novelty durability and baseline freshness from this search ledger. "
            "Distinguish snippet-only sources from opened/fetched sources. Do not claim exhaustive novelty if search or source opening is unavailable. "
            "Return {concerns:[], evidence_anchors:[], novelty:{}, pivotal_sources:[]}. Every major concern must satisfy the canonical Referee major-concern schema.\n"
            + json.dumps(ledger, ensure_ascii=False)[:30000],
            schema=S.LITERATURE_SYNTHESIS, agent_id="literature_novelty", trace_out=lit_trace,
        )
        literature_anchors = _materialize_literature_anchors(synthesis.get("evidence_anchors", []), ledger)
        anchor_map = append_evidence_anchors(
            state, literature_anchors, source_stage="LITERATURE", reviewer_id="literature_novelty"
        )
        for c in synthesis.get("concerns", []):
            _append_proposed_concern(state, c, source_agent="literature_novelty", trace=lit_trace, anchor_map=anchor_map)
        # VERIFIED_EXTERNAL_EVIDENCE is runtime-derived from actually opened
        # retriever results, never from the model's pivotal-source list.
        state.external_evidence = [
            r for row in ledger for r in (row.get("results") or [])
            if isinstance(r, dict) and _opened_content(r)
        ]
        # Independently verify every model-proposed external citation/anchor
        # against the separately retrieved source record. Model self-reported
        # verification status is never used for these metrics.
        verifier = CitationVerifier()
        state.citation_verification_records = []
        for a in state.evidence_anchors:
            if str(a.get("source_type") or "").lower() not in {"external","literature"}:
                continue
            asserted = {
                "citation_id": a.get("anchor_id"), "source_identifier": a.get("document_id") or a.get("source_identifier"),
                "title": a.get("_matched_title") or a.get("title"), "year": a.get("year"),
            }
            source_record=a.get("_matched_source_record")
            proposition=str(a.get("quote_or_fact") or "")
            record = verifier.verify(asserted, source_record, proposition=proposition)
            if record.get("proposition_support") == "uncertain" and source_record:
                raw_content=str(source_record.get("raw_content") or source_record.get("content") or source_record.get("text") or "")
                if raw_content:
                    entail_schema={"type":"object","additionalProperties":False,"required":["status","supporting_passage","contradicting_passage","confidence"],"properties":{"status":{"enum":["supported","contradicted","uncertain","not_assessable"]},"supporting_passage":{"type":"string"},"contradicting_passage":{"type":"string"},"confidence":{"type":"number","minimum":0,"maximum":1}}}
                    entail_user="ASSERTED PROPOSITION:\n"+proposition+"\n\nFROZEN SOURCE CONTENT:\n"+raw_content[:16000]
                    entail=await _call(ctx,"citation_proposition_entailment","You are an independent scientific entailment verifier. Determine whether the frozen source passage supports, contradicts, or leaves uncertain the asserted proposition. Pay special attention to negation, direction, significance, association versus causation, and scope. Do not use bibliographic identity as evidence of proposition support. Return strict JSON only.",entail_user,schema=entail_schema,model=ctx.config.verifier_model or ctx.config.model,agent_id="citation-entailment-verifier")
                    record=verifier.verify(asserted,source_record,proposition=proposition,entailment=entail)
            state.citation_verification_records.append(record)
        state.metrics["citation_metrics"] = citation_metrics(state.citation_verification_records)
        state.classification["model_pivotal_sources_unverified"] = synthesis.get("pivotal_sources", []) if isinstance(synthesis, dict) else []
        if isinstance(synthesis.get("novelty"), dict):
            state.classification["novelty_assessment"] = synthesis["novelty"]
        state.classification["literature_search_status"] = state.literature_status


class SpecialistStage(Stage):
    stage_id = "08_specialists"

    async def run(self, ctx, state):
        tasks = state.review_plan[: ctx.config.specialist_limit]
        if not tasks:
            tasks = [{"task_id": "T001", "specialist": "methods_design", "claim_ids": [], "objective": "Core methods audit"}]
        sem = asyncio.Semaphore(ctx.config.max_concurrency)

        async def run_one(task: dict[str, Any]):
            name = task["specialist"]
            skills = AVAILABLE_TASK_SKILLS[name]
            role = "You are an independent scientific specialist reviewer."
            agent_file = AGENT_FILE_MAP.get(name)
            if agent_file:
                role += "\n" + ctx.prompts.agent(agent_file)
            system = role + "\n" + "\n".join(ctx.prompts.skill(s) for s in skills) + "\n" + ctx.prompts.skill("43_major_comment_admission")
            claim_ids = set(task.get("claim_ids") or [])
            claims = [c for c in state.claims if not claim_ids or c.get("claim_id") in claim_ids]
            context = ContextManager(max_chars=18000).for_claims(state.document_map.get("documents", []), claims)
            user = (
                "Perform your assigned audit independently. Return {concerns:[], evidence_anchors:[], notes:[], uncertainty:[]}. "
                "Major concerns must use the canonical schema: claim IDs, anchors, failure mechanism, consequence, minimum resolution, testable closure criterion, numeric reviewer_confidence, steelman, steelman_survives, and steelman_survival_reason. "
                "Do not invent manuscript facts.\nTask:\n" + json.dumps(task, ensure_ascii=False) +
                "\nClaims:\n" + json.dumps(claims, ensure_ascii=False)[:10000] +
                "\nClaim-centered manuscript context with stable document locators:\n" + context
            )
            trace: dict[str, Any] = {}
            async with sem:
                out = await _call(ctx, f"specialist:{name}", system, user, schema=S.SPECIALIST_RESULT, agent_id=f"specialist:{name}:{task['task_id']}", trace_out=trace)
            return task["task_id"], name, out, trace

        results = await asyncio.gather(*(run_one(t) for t in tasks))
        for task_id, name, out, trace in results:
            state.specialist_results[task_id] = {"specialist": name, "result": out}
            if isinstance(out, dict):
                anchor_map = append_evidence_anchors(
                    state, out.get("evidence_anchors", []), source_stage="SPECIALIST",
                    reviewer_id=name, trajectory_id=task_id,
                )
                for c in out.get("concerns", []):
                    _append_proposed_concern(state, c, source_agent=name, trace=trace, task_id=task_id, anchor_map=anchor_map)


class RedTeamSteelmanStage(Stage):
    stage_id = "09_redteam_steelman"

    async def run(self, ctx, state):
        system = ctx.prompts.skill("33_red_team_steelman")
        red_trace: dict[str, Any] = {}
        out = await _call(
            ctx,
            "redteam_steelman",
            system,
            "Red-team the central claims, then steelman each proposed major concern. Return complete canonical major-concern objects, including steelman, steelman_survives, steelman_survival_reason, and numeric reviewer_confidence, plus any new evidence anchors.\nClaims:\n"
            + json.dumps(state.claims, ensure_ascii=False)[:10000]
            + "\nConcerns:\n"
            + json.dumps(state.proposed_concerns, ensure_ascii=False)[:22000],
            schema=S.REDTEAM_RESULT, agent_id="redteam_steelman", trace_out=red_trace,
        )
        if isinstance(out, dict):
            anchor_map = append_evidence_anchors(
                state, out.get("evidence_anchors", []), source_stage="REDTEAM", reviewer_id="redteam_steelman"
            )
            by_id = {c.get("concern_id"): c for c in state.proposed_concerns if c.get("concern_id")}
            by_local = {c.get("source_local_id"): c for c in state.proposed_concerns if c.get("source_local_id")}
            for raw in out.get("concerns", []):
                c = remap_concern_references(raw, claim_map=claim_alias_map(state), anchor_map={**anchor_alias_map(state), **anchor_map})
                cid = c.get("concern_id")
                target = by_id.get(cid) or by_local.get(cid)
                if target:
                    # Preserve the canonical runtime ID and provenance.
                    canonical_id = target["concern_id"]
                    provenance = {k: target.get(k) for k in ("source_local_id", "_source_agent", "_task_id", "_generator") if k in target}
                    target.update(c)
                    target["concern_id"] = canonical_id
                    target.update(provenance)
                else:
                    _append_proposed_concern(state, c, source_agent="redteam_steelman", trace=red_trace, anchor_map=anchor_map)


def _manuscript_fingerprint(state: ReviewState) -> str:
    rows = []
    for d in state.document_map.get("documents", []):
        rows.append({
            "document_id": d.get("document_id"),
            "sha256": (d.get("metadata") or {}).get("sha256") or stable_json_hash(d.get("text", "")),
        })
    return stable_json_hash(rows)


def _is_novelty_concern(c: dict[str, Any]) -> bool:
    hay = " ".join([
        str(c.get("title", "")), str(c.get("_source_agent", "")),
        " ".join(c.get("tags") or []), str(c.get("failure_mechanism", "")),
    ]).lower()
    return any(x in hay for x in ("novelty", "prior art", "baseline obsol", "state-of-the-art", "sota"))


class TrajectoryConsensusStage(Stage):
    stage_id = "09b_independent_trajectories"

    async def run(self, ctx, state):
        n = int(getattr(ctx.config, "independent_trajectories", 0) or 0)
        if n <= 1 or not state.proposed_concerns:
            state.trajectory_consensus = {"status": "not_run", "trajectories_per_concern": n}
            return
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        claim_by_id = {c.get("claim_id"): c for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        candidates = [c for c in state.proposed_concerns if isinstance(c, dict) and c.get("severity") == "major"][: ctx.config.max_major_comments * 2]
        sem = asyncio.Semaphore(ctx.config.max_concurrency)
        rows: list[dict[str, Any]] = []

        async def one(c: dict[str, Any], i: int):
            cid = c.get("concern_id") or "unassigned"
            claims = [claim_by_id.get(x) for x in c.get("claim_ids", []) if claim_by_id.get(x)]
            anchors = [anchor_by_id.get(x) for x in c.get("evidence_anchor_ids", []) if anchor_by_id.get(x)]
            trace: dict[str, Any] = {}
            async with sem:
                out = await _call(
                    ctx, f"trajectory:{cid}:{i}",
                    "You are an independent scientific review trajectory. Evaluate the proposed concern from frozen evidence only. Do not coordinate with other trajectories and do not infer truth by vote.",
                    "Return position, rationale, severity, confidence.\nConcern:\n" + json.dumps(c, ensure_ascii=False) +
                    "\nClaims:\n" + json.dumps(claims, ensure_ascii=False) +
                    "\nAnchors:\n" + json.dumps(anchors, ensure_ascii=False),
                    schema=S.TRAJECTORY,
                    agent_id=f"trajectory:{cid}:{i}", trace_out=trace,
                )
            return {"concern_id": cid, "trajectory": i, "result": out, "trace": trace}

        jobs = [one(c, i) for c in candidates for i in range(1, n + 1)]
        if jobs:
            rows = list(await asyncio.gather(*jobs))
        by_c: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_c.setdefault(row["concern_id"], []).append(row)
        summary = []
        for cid, items in by_c.items():
            counts = {"supports": 0, "rejects": 0, "uncertain": 0}
            for item in items:
                pos = item["result"].get("position", "uncertain")
                counts[pos] = counts.get(pos, 0) + 1
            consensus_trace: dict[str, Any] = {}
            consensus = await _call(
                ctx, f"trajectory_consensus:{cid}",
                "You are a separate consensus analyst. Summarize where independent trajectories agree or disagree. Never use consensus to decide whether a scientific concern is true; validity is handled by later evidence gates.",
                "Return agreement, key_disagreement, priority_signal, and do_not_use_for_validity=true.\nTrajectories:\n" + json.dumps(items, ensure_ascii=False)[:18000],
                schema=S.TRAJECTORY_CONSENSUS, agent_id=f"trajectory-consensus:{cid}", trace_out=consensus_trace,
            )
            summary.append({"concern_id": cid, "counts": counts, "trajectories": items, "consensus": consensus, "consensus_trace": consensus_trace})
        state.trajectory_consensus = {"status": "completed", "trajectories_per_concern": n, "concerns": summary, "validity_decided_elsewhere": True}
        ctx.checkpoints.write_artifact("independent_trajectory_consensus.json", state.trajectory_consensus)


class ConcernProvenanceGateStage(Stage):
    stage_id = "10_provenance_gate"

    async def run(self, ctx, state):
        known_anchors = {a.get("anchor_id") for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        known_claims = {c.get("claim_id") for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        claim_by_id = {c.get("claim_id"): c for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        integrity_report = verify_anchor_integrity(state.evidence_anchors, state.document_map.get("documents", []))
        integrity = {r.get("anchor_id"): r for r in integrity_report.get("anchors", [])}
        passed, rejected = [], []
        seen = set()
        sem = asyncio.Semaphore(ctx.config.max_concurrency)

        # Deterministic near-duplicate map across all candidate generators.
        # Duplicate status is never delegated to the synthesis model.
        from difflib import SequenceMatcher
        duplicate_of: dict[str, str] = {}
        prior_rows: list[dict[str, Any]] = []
        for raw0 in state.proposed_concerns:
            if not isinstance(raw0, dict):
                continue
            c0 = normalize_concern(raw0)
            cid0 = str(c0.get("concern_id") or "")
            txt0 = (str(c0.get("title", "")) + " " + str(c0.get("failure_mechanism", ""))).lower().strip()
            claims0 = set(c0.get("claim_ids") or [])
            for prev in prior_rows:
                if claims0 and claims0 == prev["claims"] and txt0 and SequenceMatcher(None, txt0, prev["text"]).ratio() >= 0.88:
                    duplicate_of[cid0] = prev["concern_id"]
                    break
            prior_rows.append({"concern_id": cid0, "claims": claims0, "text": txt0})

        async def assess(i: int, raw: dict[str, Any]):
            c = normalize_concern(raw)
            c.setdefault("concern_id", f"MC{i:03d}")
            c.setdefault("_source_agent", "unknown")
            fingerprint = (str(c.get("title", "")).lower().strip(), tuple(sorted(c.get("claim_ids") or [])))
            errors: list[str] = []
            if c.get("concern_id") in duplicate_of:
                errors.append(f"duplicate concern of {duplicate_of[c.get('concern_id')]}")
            if fingerprint in seen:
                errors.append("duplicate concern")
            else:
                seen.add(fingerprint)
            errors.extend(validate_major_comment(c, known_anchors, known_claims))
            citation_by_id = {r.get("citation_id"): r for r in state.citation_verification_records if isinstance(r, dict) and r.get("citation_id")}
            for aid in c.get("evidence_anchor_ids") or []:
                if (integrity.get(aid) or {}).get("status") not in {"verified", "external_verified"}:
                    errors.append(f"anchor integrity failed: {aid}")
                anchor = anchor_by_id.get(aid) or {}
                if str(anchor.get("source_type") or "").lower() in {"external", "literature"}:
                    vr = citation_by_id.get(aid)
                    if not vr:
                        errors.append(f"external decisive evidence lacks citation verification: {aid}")
                    else:
                        if vr.get("existence_status") != "verified": errors.append(f"external source existence not verified: {aid}")
                        if vr.get("metadata_status") not in {"match", "partial_match"}: errors.append(f"external source metadata mismatch/unverifiable: {aid}")
                        if vr.get("source_content_available") is not True: errors.append(f"external source content unavailable: {aid}")
                        if vr.get("proposition_support") != "supported": errors.append(f"external source does not independently support cited proposition: {aid}")
            closure = assess_closure_test(c.get("closure_criterion", ""))
            if not closure.get("actionable"):
                errors.append("closure criterion is not deterministically testable/actionable")
            if _is_novelty_concern(c) and state.literature_status.get("status") != "available":
                errors.append("novelty/prior-art concern lacks available opened scholarly evidence")
            if errors:
                c["provenance_gate"] = {"status": "failed", "errors": errors, "anchor_integrity": [integrity.get(x) for x in c.get("evidence_anchor_ids", [])]}
                return False, c
            claims = [claim_by_id[x] for x in c.get("claim_ids", [])]
            anchors = [anchor_by_id[x] for x in c.get("evidence_anchor_ids", [])]
            trace: dict[str, Any] = {}
            async with sem:
                op_cid = c.get("source_local_id") or c["concern_id"]
                entailment = await _call(
                    ctx, f"entailment:{op_cid}",
                    "You are an evidence-entailment checker. Decide only whether the cited frozen evidence supports the stated failure mechanism and whether the consequence and closure test are proportionate. Do not re-review the whole paper.",
                    "Concern:\n" + json.dumps(c, ensure_ascii=False) + "\nClaims:\n" + json.dumps(claims, ensure_ascii=False) + "\nAnchors:\n" + json.dumps(anchors, ensure_ascii=False),
                    schema=S.ENTAILMENT, agent_id=f"entailment:{c['concern_id']}", trace_out=trace,
                )
            if entailment.get("status") != "supported":
                errors.append(f"evidence entailment is {entailment.get('status')}")
            if entailment.get("consequence_proportionate") is not True:
                errors.append("scientific consequence is not proportionate to the evidence")
            if entailment.get("closure_testable") is not True:
                errors.append("closure criterion failed entailment-level testability check")
            c["provenance_gate"] = {
                "status": "passed" if not errors else "failed", "errors": errors,
                "anchor_integrity": [integrity.get(x) for x in c.get("evidence_anchor_ids", [])],
                "entailment": entailment, "entailment_trace": trace,
            }
            return not errors, c

        rows = await asyncio.gather(*(assess(i, c) for i, c in enumerate(state.proposed_concerns, 1) if isinstance(c, dict)))
        for ok, c in rows:
            if ok:
                passed.append(c)
            else:
                c["status"] = "rejected_by_provenance_gate"
                c["admission_errors"] = list((c.get("provenance_gate") or {}).get("errors") or [])
                rejected.append(c)
        state.provenance_candidates = passed
        state.rejected_concerns.extend(rejected)
        ctx.checkpoints.write_artifact("provenance_gate.json", {
            "passed": passed, "rejected": rejected, "anchor_integrity": integrity_report,
        })


class ConcernVerificationStage(Stage):
    stage_id = "11_concern_verification"

    async def run(self, ctx, state):
        if not state.provenance_candidates:
            state.verification_candidates = []
            return

        # This prompt is deliberately separate from the reviewer prompt. The
        # verifier is blind to generator/red-team reasoning and source identity.
        system = ctx.prompts.core("INDEPENDENT_VERIFIER_PROMPT.md")
        sem = asyncio.Semaphore(ctx.config.max_concurrency)
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        claim_by_id = {c.get("claim_id"): c for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        known_anchors = set(anchor_by_id)
        known_claims = set(claim_by_id)
        manuscript_hash = _manuscript_fingerprint(state)
        integrity_report = verify_anchor_integrity(state.evidence_anchors, state.document_map.get("documents", []))
        integrity = {r.get("anchor_id"): r for r in integrity_report.get("anchors", [])}
        manuscript_for_judge = _compact_docs(state, 30000)

        async def verify(c: dict[str, Any]):
            canonical = Concern.from_dict(c)
            anchors = [anchor_by_id[a] for a in canonical.evidence_anchor_ids]
            claims = [claim_by_id[x] for x in canonical.claim_ids]
            frozen_evidence = {
                "claims": claims,
                "anchors": anchors,
                "manuscript_sha256": manuscript_hash,
                "claim_registry_sha256": stable_json_hash(claims),
                "anchor_bundle_sha256": stable_json_hash(anchors),
            }
            hashes = {
                "manuscript_sha256": manuscript_hash,
                "claim_registry_sha256": frozen_evidence["claim_registry_sha256"],
                "anchor_bundle_sha256": frozen_evidence["anchor_bundle_sha256"],
                "concern_sha256": stable_json_hash(canonical.scientific_payload()),
            }
            generator = c.get("_generator") or {}
            verifier_context = f"ctx-verifier-{uuid.uuid4().hex}"
            verifier_agent = f"verifier:{canonical.concern_id}:{uuid.uuid4().hex[:10]}"
            trace: dict[str, Any] = {}
            async with sem:
                verdict = await _call(
                    ctx,
                    f"concern_verifier:{c.get('source_local_id') or canonical.concern_id}",
                    system,
                    "MANUSCRIPT (UNTRUSTED DATA):\n" + manuscript_for_judge
                    + "\n\nFROZEN_EVIDENCE_BUNDLE:\n" + json.dumps(frozen_evidence, ensure_ascii=False)[:18000]
                    + "\n\nPROPOSED_CONCERN:\n" + json.dumps(canonical.scientific_payload(), ensure_ascii=False),
                    schema=S.VERIFIER,
                    model=ctx.config.verifier_model or ctx.config.model,
                    agent_id=verifier_agent,
                    context_id=verifier_context,
                    trace_out=trace,
                )

            # Referee does not trust the judge's status as proof. Recompute all
            # mechanically checkable invariants after receiving its JSON.
            post_errors: list[str] = []
            post_errors.extend(validate_major_comment(canonical.to_dict(), known_anchors, known_claims))
            for aid in canonical.evidence_anchor_ids:
                if (integrity.get(aid) or {}).get("status") not in {"verified", "external_verified"}:
                    post_errors.append(f"anchor failed deterministic integrity check: {aid}")
            closure = assess_closure_test(canonical.closure_criterion)
            if not closure.get("actionable"):
                post_errors.append("closure criterion failed deterministic actionability check")
            gate = c.get("provenance_gate") or {}
            if gate.get("status") != "passed":
                post_errors.append("pre-verifier provenance gate did not pass")
            ent0 = gate.get("entailment") or {}
            if ent0.get("status") != "supported" or ent0.get("consequence_proportionate") is not True or ent0.get("closure_testable") is not True:
                post_errors.append("pre-verifier entailment gate did not fully pass")

            if generator.get("context_id") and generator.get("context_id") == trace.get("context_id"):
                post_errors.append("verifier context is not independent from generator context")
            if generator.get("agent_id") and generator.get("agent_id") == trace.get("agent_id"):
                post_errors.append("verifier identity is not independent from generator identity")

            # Recompute frozen hashes after the judge returns. Any mutation makes
            # the verification unusable even if the judge wrote 'verified'.
            current_hashes = {
                "manuscript_sha256": _manuscript_fingerprint(state),
                "claim_registry_sha256": stable_json_hash([claim_by_id[x] for x in canonical.claim_ids]),
                "anchor_bundle_sha256": stable_json_hash([anchor_by_id[a] for a in canonical.evidence_anchor_ids]),
                "concern_sha256": stable_json_hash(Concern.from_dict(c).scientific_payload()),
            }
            for key, frozen_value in hashes.items():
                if current_hashes.get(key) != frozen_value:
                    post_errors.append(f"frozen bundle changed during verification: {key}")

            judge_status = verdict.get("status")
            judge_ent = verdict.get("entailment") or {}
            required_true = (
                "claim_mapping_valid", "anchors_support_failure_mechanism",
                "scientific_consequence_proportionate", "minimum_resolution_sufficient",
                "closure_criterion_testable", "steelman_survival_supported",
            )
            if judge_status == "verified":
                for key in required_true:
                    if judge_ent.get(key) is not True:
                        post_errors.append(f"independent judge did not affirm {key}")
                if judge_ent.get("manuscript_contradiction_found") is not False:
                    post_errors.append("independent judge found or could not exclude a manuscript contradiction")

            if post_errors:
                computed_status = "rejected"
            elif judge_status == "verified":
                computed_status = "verified"
            elif judge_status == "uncertain":
                computed_status = "uncertain"
            else:
                computed_status = "rejected"

            record = {
                "concern_id": canonical.concern_id,
                "verifier_prompt_sha256": __import__("hashlib").sha256(system.encode("utf-8")).hexdigest(),
                "generator_run_id": generator.get("request_id"),
                "generator_agent_id": generator.get("agent_id"),
                "generator_context_id": generator.get("context_id"),
                "generator_model": generator.get("model"),
                "verifier_run_id": trace.get("request_id"),
                "verifier_agent_id": trace.get("agent_id"),
                "verifier_context_id": trace.get("context_id"),
                "verifier_model": trace.get("model"),
                **hashes,
                "verification_status": computed_status,
                "judge_status": judge_status,
                "verifier_output_sha256": stable_json_hash(verdict),
                "verdict": verdict,
                "deterministic_postcheck": {
                    "status": "passed" if not post_errors else "failed",
                    "errors": post_errors,
                    "model_status_trusted_as_proof": False,
                    "anchor_integrity": [integrity.get(a) for a in canonical.evidence_anchor_ids],
                    "closure": closure,
                    "hashes_recomputed": current_hashes,
                },
            }
            if ctx.config.mode == "exhaustive" and ctx.config.verifier_model and record.get("generator_model") == record.get("verifier_model"):
                record["model_independence_warning"] = "exhaustive mode configured a verifier model identical to the generator model"
            return c, record

        results = await asyncio.gather(*(verify(c) for c in state.provenance_candidates))
        verified, rejected = [], []
        for c, record in results:
            state.verification_records.append(record)
            status = record.get("verification_status")
            if status == "verified":
                c["status"] = "verified_pending_admission"
                verified.append(c)
            else:
                c["status"] = f"rejected_after_verification:{status}"
                c["admission_errors"] = [f"computed independent verification status: {status}"] + list((record.get("deterministic_postcheck") or {}).get("errors") or [])
                rejected.append(c)
        state.verification_candidates = verified
        state.rejected_concerns.extend(rejected)
        ctx.checkpoints.write_artifact("independent_verification.json", state.verification_records)


class ConcernAdmissionStage(Stage):
    stage_id = "12_concern_admission"

    async def run(self, ctx, state):
        known_anchors = {a.get("anchor_id") for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        known_claims = {c.get("claim_id") for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict)}
        claim_by_id = {c.get("claim_id"): c for c in state.claims if isinstance(c, dict)}
        records = {r.get("concern_id"): r for r in state.verification_records}
        manuscript_hash = _manuscript_fingerprint(state)
        admitted, rejected = [], []
        for raw in state.verification_candidates:
            c = normalize_concern(raw)
            cid = c.get("concern_id")
            errors = validate_major_comment(c, known_anchors, known_claims)
            if (c.get("provenance_gate") or {}).get("status") != "passed":
                errors.append("provenance gate did not pass")
            rec = records.get(cid)
            if not rec or rec.get("verification_status") != "verified":
                errors.append("missing successful independent verification")
            else:
                canonical = Concern.from_dict(c)
                claims = [claim_by_id[x] for x in canonical.claim_ids]
                anchors = [anchor_by_id[x] for x in canonical.evidence_anchor_ids]
                current = {
                    "manuscript_sha256": manuscript_hash,
                    "claim_registry_sha256": stable_json_hash(claims),
                    "anchor_bundle_sha256": stable_json_hash(anchors),
                    "concern_sha256": stable_json_hash(canonical.scientific_payload()),
                }
                for key, value in current.items():
                    if rec.get(key) != value:
                        errors.append(f"frozen verification hash invalidated: {key}")
            if errors:
                c["status"] = "rejected_at_final_admission"
                c["admission_errors"] = errors
                rejected.append(c)
            else:
                c["status"] = "admitted"
                c["independent_verification"] = {k: rec.get(k) for k in (
                    "verification_status", "verifier_run_id", "verifier_agent_id", "verifier_context_id", "verifier_model", "verifier_output_sha256"
                )}
                admitted.append(c)
        state.admitted_concerns = admitted[: ctx.config.max_major_comments]
        state.rejected_concerns.extend(rejected)
        ctx.checkpoints.write_artifact("concern_admission_log.json", {"admitted": state.admitted_concerns, "rejected": state.rejected_concerns})


class PriorityPairwiseStage(Stage):
    stage_id = "12b_priority_pairwise"

    async def run(self, ctx, state):
        concerns = list(state.admitted_concerns)
        if len(concerns) < 2 or not getattr(ctx.config, "enable_pairwise_priority", True):
            state.priority_ranking = [{"concern_id": c.get("concern_id"), "score": 0.0, "comparisons": 0} for c in concerns]
            return
        pairs = []
        for i in range(len(concerns)):
            for j in range(i + 1, len(concerns)):
                pairs.append((concerns[i], concerns[j]))
        pairs = pairs[: int(getattr(ctx.config, "pairwise_priority_budget", 12) or 12)]
        sem = asyncio.Semaphore(ctx.config.max_concurrency)
        scores = {c.get("concern_id"): {"wins": 0.0, "comparisons": 0} for c in concerns}

        async def one(a, b):
            async with sem:
                return a, b, await _call(
                    ctx, f"priority:{a.get('concern_id')}:{b.get('concern_id')}",
                    "Both concerns are already independently verified as scientifically valid. Compare only their threat to the manuscript's central claims. Do not use this comparison to decide truth.",
                    "Return winner as one concern_id or 'tie', with rationale.\nA:\n" + json.dumps(a, ensure_ascii=False) + "\nB:\n" + json.dumps(b, ensure_ascii=False),
                    schema=S.PAIRWISE,
                    agent_id=f"priority-judge:{uuid.uuid4().hex[:10]}",
                )
        rows = await asyncio.gather(*(one(a, b) for a, b in pairs))
        detail = []
        for a, b, out in rows:
            ca, cb = a.get("concern_id"), b.get("concern_id")
            scores[ca]["comparisons"] += 1; scores[cb]["comparisons"] += 1
            winner = out.get("winner")
            if winner == ca: scores[ca]["wins"] += 1
            elif winner == cb: scores[cb]["wins"] += 1
            else: scores[ca]["wins"] += .5; scores[cb]["wins"] += .5
            detail.append({"a": ca, "b": cb, "winner": winner, "rationale": out.get("rationale")})
        ranking = []
        for cid, row in scores.items():
            ranking.append({"concern_id": cid, "score": round(row["wins"] / max(1, row["comparisons"]), 4), **row})
        state.priority_ranking = sorted(ranking, key=lambda x: (-x["score"], x["concern_id"] or ""))
        ctx.checkpoints.write_artifact("priority_pairwise.json", {"ranking": state.priority_ranking, "comparisons": detail})


class ReliabilityStage(Stage):
    stage_id = "12_reliability"

    async def run(self, ctx, state):
        if not ctx.config.enable_reliability_pass or ctx.config.repeatability_claims <= 0:
            state.reliability = {"status": "not_run", "reason": "mode/config"}
            return
        top = state.admitted_concerns[: ctx.config.repeatability_claims]
        system = ctx.prompts.skill("40_review_reliability_repeatability")
        out = await _call(
            ctx,
            "reliability",
            system,
            "Independently reassess these decisive concerns from frozen artifacts. Return stability, agreements, disagreements, and any downgrade recommendations.\n"
            + json.dumps(top, ensure_ascii=False)[:16000],
            schema=S.RELIABILITY,
        )
        state.reliability = out if isinstance(out, dict) else {"status": "unassessable"}


class GateAndSynthesisStage(Stage):
    stage_id = "13_gates_synthesis"

    async def run(self, ctx, state):
        system = (
            ctx.prompts.core("VALIDATION_LADDER.md")
            + "\n"
            + ctx.prompts.core("OUTPUT_CONTRACT.md")
            + "\n"
            + ctx.prompts.skill("32_review_synthesis")
            + "\n"
            + ctx.prompts.skill("42_review_bias_fairness")
        )
        out = await _call(
            ctx,
            "final_synthesis",
            system,
            "Apply critical gates and synthesize a progressive-disclosure peer review. Do not average away failed gates. "
            "Do not generate acceptance probability. Do not add new major comments that did not pass provenance, independent verification, and final admission. "
            "Return {critical_gates:{}, final_review:{decision_brief:{}, minor_comments:[], strengths:[], limitations:[]}}.\n"
            "Core peer-review output (major concerns here are NOT automatically admitted):\n"
            + json.dumps(state.core_review, ensure_ascii=False)[:16000]
            + "\nVerified concerns:\n"
            + json.dumps(state.admitted_concerns, ensure_ascii=False)[:18000]
            + "\nReliability:\n"
            + json.dumps(state.reliability, ensure_ascii=False)[:8000],
            schema=S.FINAL_SYNTHESIS,
        )
        state.critical_gates = out.get("critical_gates", {}) if isinstance(out, dict) else {}
        state.final_review = out.get("final_review", {}) if isinstance(out, dict) else {}
        ranking={r.get("concern_id"):r for r in state.priority_ranking}
        state.final_review["major_comments"] = sorted(state.admitted_concerns, key=lambda c: (-(ranking.get(c.get("concern_id"),{}).get("score",0.0)), c.get("concern_id", "")))
        # Preserve validated core-review material instead of discarding it during
        # synthesis. Major comments remain exclusively the independently admitted set.
        core = state.core_review or {}
        if core.get("minor_concerns"):
            state.final_review["minor_comments"] = list(core.get("minor_concerns") or []) + list(state.final_review.get("minor_comments") or [])
        if core.get("strengths"):
            state.final_review["strengths"] = list(core.get("strengths") or []) + list(state.final_review.get("strengths") or [])
        state.final_review["observations"] = list(core.get("observations") or [])
        state.final_review["manuscript_summary"] = core.get("manuscript_summary", {})
        state.final_review["core_review_summary"] = core.get("review_summary", {})
        state.final_review["novelty_assessment"] = core.get("novelty_assessment", {})
        state.final_review["reproducibility_assessment"] = core.get("reproducibility_assessment", {})
        state.final_review["numerical_consistency"] = core.get("numerical_consistency", {})
        state.final_review["priority_ranking"] = state.priority_ranking
        state.final_review["literature_search_status"] = state.literature_status
        state.final_review["policy_status"] = state.policy_status


class JournalStage(Stage):
    stage_id = "14_journal_calibration"

    async def run(self, ctx, state):
        if not ctx.config.enable_journal_calibration:
            return
        system = ctx.prompts.skill("30_journal_calibration") + "\n" + ctx.prompts.core("TEN_JOURNAL_ENGINE.md")
        out = await _call(
            ctx,
            "journal_calibration",
            system,
            "Calibrate a plausible journal landscape only after scientific judgments are fixed. Never pad the list. "
            "Return {journals:[]}. Mark unverifiable scope/currentness explicitly if no live journal evidence is available.\nClassification:\n"
            + json.dumps(state.classification, ensure_ascii=False)[:10000]
            + "\nGates:\n"
            + json.dumps(state.critical_gates, ensure_ascii=False)[:8000],
            schema=S.JOURNAL,
        )
        journals = out.get("journals", []) if isinstance(out, dict) else []
        state.journal_landscape = journals[: ctx.config.journal_candidate_target]
        state.final_review["journal_landscape"] = state.journal_landscape
