from __future__ import annotations

import asyncio
import hashlib
import json
import re
from difflib import SequenceMatcher
from typing import Any

from .base import Stage
from .core import (
    IntakeStage, PolicySecurityStage, _call, _core_review_user_payload,
    _compact_docs, _enrich_search_result, _opened_content,
    _materialize_literature_anchors, _manuscript_fingerprint,
)
from .platform import PackageAuditStage, ReportingAuditStage, ReproducibilityAuditStage, ProvenanceAuditStage
from ..context_manager import ContextManager
from ..contracts import Concern, validate_json_contract, schemas as S
from ..contracts.review import (
    CORE_REVIEW_OUTPUT, CORE_SPECIALIST_RESULT, CORE_VERIFIER,
    CORE_SCORECARD, CORE_TARGET_JOURNAL,
)
from ..models import ReviewState
from ..utils.hashing import stable_json_hash
from ..validation import validate_major_comment
from ..validation.identifiers import (
    append_evidence_anchors, canonicalize_core_claims, claim_alias_map,
    anchor_alias_map, remap_concern_references, allocate_concern_id, assert_unique_ids,
)
from ..verification import verify_anchor_integrity, assess_closure_test, CitationVerifier, citation_metrics
from ..benchmarking import (
    load_benchmark_profile, load_journal_profile, scorecard_summary, compare_to_benchmark,
)


CORE_SKILL_FAMILIES: dict[str, list[str]] = {
    "theory": ["09_construct_theory", "10_rival_theory_falsifiability"],
    "methods": ["11_empirical_design", "12_sampling_measurement"],
    "statistics_causal": ["13_causal_inference", "14_statistics"],
    "literature": ["04_reference_forensics", "05_literature_search", "07_novelty", "08_research_gap", "39_literature_search_provenance"],
    "computational": ["15_benchmark_epistemology", "16_model_validation", "17_ml_ai", "18_computational_simulation", "50_computational_science_numerics", "51_ml_for_science"],
    "reproducibility": ["26_code_reproducibility", "27_robustness_generalization", "29_reporting_guidelines"],
    "numerical": ["25_figures_tables", "38_equations_units_numerical_consistency"],
    "integrity": ["28_ethics_integrity", "37_retraction_citation_integrity", "42_review_bias_fairness"],
    "systematic_review_meta": ["19_systematic_review_meta"],
    "qualitative": ["20_qualitative"],
    "rct_intervention": ["21_rct_intervention"],
    "observational_epidemiology": ["22_observational_epidemiology"],
    "diagnostic_prognostic": ["23_diagnostic_prognostic"],
    "measurement_instrument": ["24_measurement_instrument"],
    "electrochemistry_fuel_cells": ["44_electrochemistry_fuel_cells", "52_experimental_metrology_uncertainty"],
    "materials_characterization": ["45_materials_characterization", "48_analytical_chemistry_measurement", "54_spectroscopy_microscopy"],
    "environmental_process": ["46_environmental_water_processes", "49_energy_lca_tea", "53_chemical_kinetics_transport", "55_scaleup_process_engineering"],
    "microbiology_omics": ["47_microbiology_biofilms_omics"],
    "energy_lca_tea": ["49_energy_lca_tea", "55_scaleup_process_engineering"],
    "metrology_measurement": ["48_analytical_chemistry_measurement", "52_experimental_metrology_uncertainty"],
}


NOVELTY_TERMS = (
    "novelty", "prior art", "precedent", "already established", "state-of-the-art",
    "state of the art", "sota", "baseline obsolete", "baseline outdated", "existing work",
    "previously demonstrated", "established theory", "first to", "unprecedented",
)


def _is_novelty_concern(c: dict[str, Any]) -> bool:
    hay = " ".join(
        [
            str(c.get("title", "")),
            str(c.get("failure_mechanism", "")),
            str(c.get("scientific_consequence", "")),
            " ".join(str(x) for x in (c.get("uncertainties") or [])),
        ]
    ).lower()
    return any(term in hay for term in NOVELTY_TERMS)


def _claim_is_novelty_or_sota(c: dict[str, Any]) -> bool:
    text = (str(c.get("text", "")) + " " + str(c.get("claim_type", ""))).lower()
    strong = (
        "novelty", "first ", "first-", "unprecedented", "state-of-the-art", "state of the art",
        "sota", "outperforms all", "no previous", "existing methods cannot", "new framework",
    )
    return str(c.get("claim_type", "")).lower() == "novelty" or any(x in text for x in strong)


def _dedupe_specialist_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate specialist-family tasks into one bounded claim audit.

    A specialist family consumes one execution slot. Overlapping requests for
    the same family are merged by unioning claim IDs and evidence needs while
    preserving the strongest priority/required-safety metadata.
    """
    by_family: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    rank = {"low": 1, "medium": 2, "high": 3}
    for task in tasks:
        family = str(task.get("specialist") or "")
        if not family:
            continue
        if family not in by_family:
            by_family[family] = dict(task)
            by_family[family]["claim_ids"] = list(dict.fromkeys(str(x) for x in (task.get("claim_ids") or [])))[:12]
            by_family[family]["evidence_needs"] = list(dict.fromkeys(str(x) for x in (task.get("evidence_needs") or [])))[:12]
            order.append(family)
            continue
        cur = by_family[family]
        cur["claim_ids"] = list(dict.fromkeys([
            *(str(x) for x in (cur.get("claim_ids") or [])),
            *(str(x) for x in (task.get("claim_ids") or [])),
        ]))[:12]
        cur["evidence_needs"] = list(dict.fromkeys([
            *(str(x) for x in (cur.get("evidence_needs") or [])),
            *(str(x) for x in (task.get("evidence_needs") or [])),
        ]))[:12]
        if task.get("_deterministic_required"):
            cur["_deterministic_required"] = True
        if rank.get(str(task.get("priority") or "medium"), 2) > rank.get(str(cur.get("priority") or "medium"), 2):
            cur["priority"] = task.get("priority")
        objective = str(task.get("objective") or "").strip()
        if objective and objective not in str(cur.get("objective") or ""):
            cur["objective"] = (str(cur.get("objective") or "") + " | " + objective).strip(" |")
    return [by_family[k] for k in order]


def _fallback_specialist_requests(state: ReviewState) -> list[dict[str, Any]]:
    """Deterministic required-specialist safety net for Core.

    The core reviewer remains the primary router, but obvious proof burdens are
    always merged into its plan. This protects against incomplete as well as
    empty specialist routing.
    """
    classification = state.classification or {}
    claims = [c for c in state.claims if isinstance(c, dict)]
    blob = " ".join(
        [json.dumps(classification, ensure_ascii=False)]
        + [str(c.get("text", "")) + " " + str(c.get("claim_type", "")) for c in claims]
    ).lower()
    families: list[str] = []

    def add(name: str) -> None:
        if name in CORE_SKILL_FAMILIES and name not in families:
            families.append(name)

    design = str(classification.get("design") or "").lower()
    inference = str(classification.get("inference_type") or "").lower()
    study_type = str(classification.get("study_type") or "").lower()

    if "random" in blob or "trial" in design or "rct" in blob:
        add("rct_intervention")
    if "causal" in inference or any(str(c.get("claim_type", "")).lower() == "causal" for c in claims):
        add("statistics_causal")
        add("methods")
    if any(x in study_type + " " + design for x in ("empirical", "observational", "experimental", "cohort", "case-control")):
        add("methods")
    if any(x in blob for x in ("machine learning", "deep learning", "neural network", "benchmark", "classifier", "foundation model", "llm")):
        add("computational")
    if any(x in study_type + " " + design for x in ("theory", "theoretical", "conceptual")) or any(str(c.get("claim_type", "")).lower() == "theoretical" for c in claims):
        add("theory")
    if any(_claim_is_novelty_or_sota(c) for c in claims):
        add("literature")
    if any(x in blob for x in ("meta-analysis", "systematic review", "systematic-review")):
        add("systematic_review_meta")
    if any(x in blob for x in ("qualitative", "interview", "thematic analysis")):
        add("qualitative")
    if any(x in blob for x in ("diagnostic", "prognostic", "auc", "sensitivity", "specificity")):
        add("diagnostic_prognostic")
    if any(x in blob for x in ("instrument", "scale validation", "measurement model", "psychometric")):
        add("measurement_instrument")

    if not families:
        add("methods" if any(x in study_type + " " + design for x in ("empirical", "observational", "experimental")) else "theory")

    claim_ids = [str(c.get("claim_id")) for c in claims if c.get("claim_id")][:8]
    return [
        {
            "task_id": f"LF{i:03d}",
            "specialist": family,
            "claim_ids": claim_ids,
            "objective": f"Deterministic Core safety audit from the {family} perspective",
            "priority": "high" if family in {"statistics_causal", "literature", "rct_intervention", "computational"} else "medium",
            "evidence_needs": [],
            "_deterministic_required": True,
        }
        for i, family in enumerate(families, 1)
    ]


def _task_priority_score(task: dict[str, Any]) -> float:
    family = str(task.get("specialist") or "")
    priority = {"high": 30.0, "medium": 20.0, "low": 10.0}.get(str(task.get("priority") or "medium"), 20.0)
    required_bonus = 45.0 if task.get("_deterministic_required") else 0.0
    safety = {
        "statistics_causal": 20.0,
        "rct_intervention": 20.0,
        "literature": 18.0,
        "numerical": 17.0,
        "computational": 15.0,
        "methods": 13.0,
        "theory": 12.0,
        "reproducibility": 10.0,
    }.get(family, 8.0)
    claim_bonus = min(8.0, 1.5 * len(task.get("claim_ids") or []))
    return priority + required_bonus + safety + claim_bonus


def _rank_specialist_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Stable deterministic ranking; ties preserve original order.
    return [x[1] for x in sorted(enumerate(tasks), key=lambda pair: (-_task_priority_score(pair[1]), pair[0]))]


def _token_set(text: str) -> set[str]:
    stop = {
        "about", "after", "again", "against", "because", "being", "between", "could", "does",
        "from", "have", "into", "manuscript", "result", "results", "their", "there", "these",
        "this", "those", "through", "using", "which", "with", "would", "claim", "claims",
        "study", "paper", "authors", "analysis", "reported", "reporting",
    }
    return {x for x in re.findall(r"[a-z][a-z0-9_-]{3,}", text.lower()) if x not in stop}


_CONCERN_CONCEPTS: dict[str, tuple[str, ...]] = {
    "confounding_causal": ("confound", "causal", "identif", "randomiz", "treatment allocation", "endogeneity"),
    "data_leakage": ("leakage", "data leak", "train-test", "training test", "cross-validation", "cross validation"),
    "multiplicity": ("multiple testing", "multiplicity", "family-wise", "false discovery", "p-hacking"),
    "sampling_power": ("sample size", "power", "underpowered", "sampling", "selection bias"),
    "measurement": ("measurement", "reliability", "validity", "instrument", "construct"),
    "uncertainty": ("confidence interval", "uncertainty", "standard error", "effect size"),
    "robustness": ("robust", "sensitivity", "ablation", "generaliz", "replicat"),
    "model_validation": ("validation", "holdout", "external validation", "overfit", "calibration"),
    "baseline_fairness": ("baseline", "comparator", "benchmark", "fair comparison"),
    "novelty_prior_art": NOVELTY_TERMS,
    "reproducibility": ("reproduc", "code", "environment", "data availability", "seed"),
    "missing_data": ("missing data", "imputation", "attrition", "dropout"),
}


def _concern_concepts(c: dict[str, Any]) -> set[str]:
    text = " ".join(str(c.get(k) or "") for k in ("title", "failure_mechanism", "scientific_consequence", "minimum_resolution")).lower()
    return {name for name, terms in _CONCERN_CONCEPTS.items() if any(term in text for term in terms)}


def _concerns_semantically_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ac = set(str(x) for x in (a.get("claim_ids") or []))
    bc = set(str(x) for x in (b.get("claim_ids") or []))
    if not ac or not bc:
        return False
    claim_jaccard = len(ac & bc) / max(1, len(ac | bc))
    if claim_jaccard < 0.5:
        return False

    at = " ".join(str(a.get(k) or "") for k in ("title", "failure_mechanism", "scientific_consequence"))
    bt = " ".join(str(b.get(k) or "") for k in ("title", "failure_mechanism", "scientific_consequence"))
    seq = SequenceMatcher(None, at.lower(), bt.lower()).ratio()
    ta, tb = _token_set(at), _token_set(bt)
    tok = len(ta & tb) / max(1, len(ta | tb))
    concepts_a, concepts_b = _concern_concepts(a), _concern_concepts(b)
    concept_overlap = bool(concepts_a & concepts_b)

    return seq >= 0.72 or tok >= 0.48 or (concept_overlap and (seq >= 0.38 or tok >= 0.28))


def _quantitative_density_trigger(state: ReviewState) -> bool:
    text = "\n".join(str(d.get("text") or "") for d in state.document_map.get("documents", []))[:120000]
    indicators = 0
    patterns = (
        r"\b(?:p\s*[<=>]|confidence interval|\bCI\b|standard deviation|standard error)\b",
        r"\b(?:n\s*=|sample size|participants|subjects|patients)\b",
        r"\b(?:accuracy|f1|auc|rmse|mae|r\^?2|effect size|odds ratio|hazard ratio)\b",
        r"\b\d+(?:\.\d+)?%",
        r"\b(?:equation|theorem|lemma|table\s+\d+|figure\s+\d+)\b",
    )
    lower = text.lower()
    for pat in patterns:
        if re.search(pat, lower, flags=re.I):
            indicators += 1
    return indicators >= 3


def _validate_core_material(state: ReviewState, out: dict[str, Any]) -> dict[str, Any]:
    known_claims = {str(c.get("claim_id")) for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
    known_anchors = {str(a.get("anchor_id")) for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
    cmap = claim_alias_map(state)
    amap = anchor_alias_map(state)
    errors: list[str] = []
    warnings: list[str] = []

    def refs(label: str, rows: list[Any]) -> None:
        seen_ids: set[str] = set()
        for i, row in enumerate(rows or [], 1):
            if not isinstance(row, dict):
                continue
            rid = str(row.get("concern_id") or row.get("observation_id") or row.get("id") or "")
            if rid:
                if rid in seen_ids:
                    warnings.append(f"duplicate local {label} id: {rid}")
                seen_ids.add(rid)
            cids = [cmap.get(str(x), str(x)) for x in (row.get("claim_ids") or [])]
            aids = [amap.get(str(x), str(x)) for x in (row.get("evidence_anchor_ids") or row.get("anchor_ids") or [])]
            bad_c = sorted(set(cids) - known_claims)
            bad_a = sorted(set(aids) - known_anchors)
            if bad_c:
                warnings.append(f"{label}[{i}] unknown claims: {bad_c}")
            if bad_a:
                warnings.append(f"{label}[{i}] unknown anchors: {bad_a}")

    refs("candidate_concern", out.get("candidate_concerns") or [])
    refs("minor_concern", out.get("minor_concerns") or [])
    refs("strength", out.get("strengths") or [])
    refs("observation", out.get("observations") or [])

    if not state.claims:
        errors.append("core reviewer returned no canonical claims")
    if not state.evidence_anchors:
        warnings.append("core reviewer returned no manuscript evidence anchors")

    return {
        "status": "failed" if errors else ("passed_with_warnings" if warnings else "passed"),
        "errors": errors,
        "warnings": warnings,
    }


def _sanitize_core_auxiliary_items(state: ReviewState, out: dict[str, Any]) -> dict[str, Any]:
    """Drop auxiliary dict items with unresolved explicit references.

    Free-form strings are retained. Dict items are retained when they either
    have no explicit references or all explicit claim/anchor references resolve.
    """
    known_claims = {str(c.get("claim_id")) for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
    known_anchors = {str(a.get("anchor_id")) for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
    cmap = claim_alias_map(state)
    amap = anchor_alias_map(state)
    dropped: list[dict[str, Any]] = []

    for key in ("minor_concerns", "strengths", "observations"):
        cleaned: list[Any] = []
        for item in list(out.get(key) or []):
            if not isinstance(item, dict):
                cleaned.append(item)
                continue
            cids = [cmap.get(str(x), str(x)) for x in (item.get("claim_ids") or [])]
            aids = [amap.get(str(x), str(x)) for x in (item.get("evidence_anchor_ids") or item.get("anchor_ids") or [])]
            if (cids and not set(cids).issubset(known_claims)) or (aids and not set(aids).issubset(known_anchors)):
                dropped.append({"collection": key, "item": item})
                continue
            if "claim_ids" in item:
                item = dict(item); item["claim_ids"] = cids
            if "evidence_anchor_ids" in item:
                item = dict(item); item["evidence_anchor_ids"] = aids
            cleaned.append(item)
        out[key] = cleaned
    if dropped:
        state.mode_artifacts["core_dropped_auxiliary_items"] = dropped
        state.warnings.append(f"Dropped {len(dropped)} auxiliary core-review item(s) with unresolved explicit references.")
    return out


def _candidate_public_payload(c: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "concern_id", "title", "severity", "claim_ids", "evidence_anchor_ids",
        "failure_mechanism", "scientific_consequence", "minimum_resolution",
        "closure_criterion", "reviewer_confidence", "external_verification_required",
        "uncertainties", "suggested_validation_checks",
    )
    return {k: c.get(k) for k in allowed if k in c}


def _contradiction_context(state: ReviewState, concern: dict[str, Any], claims: list[dict[str, Any]], max_chars: int = 8000) -> str:
    seed = " ".join(
        [str(concern.get("title") or ""), str(concern.get("failure_mechanism") or "")]
        + [str(c.get("text") or "") for c in claims]
    )
    stop = {
        "about", "after", "again", "against", "because", "being", "between", "could", "does",
        "from", "have", "into", "manuscript", "result", "results", "their", "there", "these",
        "this", "those", "through", "using", "which", "with", "would", "claim", "claims",
    }
    terms = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", seed) if w.lower() not in stop]
    terms = list(dict.fromkeys(terms))[:24]
    chunks: list[str] = []
    used = 0
    for d in state.document_map.get("documents", []):
        text = str(d.get("text") or "")
        lower = text.lower()
        hits: list[int] = []
        for term in terms:
            start = 0
            while len(hits) < 8:
                pos = lower.find(term, start)
                if pos < 0:
                    break
                hits.append(pos)
                start = pos + len(term)
        for pos in sorted(set(hits))[:6]:
            start = max(0, pos - 650)
            end = min(len(text), pos + 1150)
            piece = text[start:end]
            if used + len(piece) > max_chars:
                piece = piece[: max(0, max_chars - used)]
            if not piece:
                return "\n\n".join(chunks)
            chunks.append(f"### {d.get('document_id')} chars {start}-{start+len(piece)}\n{piece}")
            used += len(piece)
            if used >= max_chars:
                return "\n\n".join(chunks)
    return "\n\n".join(chunks)


def _scientific_consequence_weight(c: dict[str, Any]) -> float:
    text = (str(c.get("scientific_consequence") or "") + " " + str(c.get("failure_mechanism") or "")).lower()
    if any(x in text for x in ("invalidat", "cannot support", "not identifiable", "uninterpretable", "principal conclusion", "central conclusion is unsupported", "main conclusion is unsupported")):
        return 4.0
    if any(x in text for x in ("major reinterpret", "reframe", "materially changes", "central interpretation", "primary result")):
        return 3.0
    if any(x in text for x in ("substantial", "important limitation", "material bias", "serious limitation", "weakens")):
        return 2.0
    return 1.0


def _scientific_gates(state: ReviewState) -> dict[str, dict[str, Any]]:
    """Conservative readiness gates.

    A missing verified flaw is not affirmative proof of soundness. Gates report
    assessment depth explicitly and use NO_VERIFIED_BARRIER / NOT_ASSESSED
    rather than an overconfident PASS.
    """
    admitted = list(state.admitted_concerns or [])
    texts = [
        (str(c.get("title") or "") + " " + str(c.get("failure_mechanism") or "") + " " + str(c.get("scientific_consequence") or "")).lower()
        for c in admitted
    ]
    has_major = bool(admitted)
    uncertainty = bool((state.core_review or {}).get("remaining_uncertainties"))
    novelty_major = any(_is_novelty_concern(c) for c in admitted)
    methods_major = any(any(k in t for k in ("design", "method", "sampling", "measurement", "confound", "causal", "identification")) for t in texts)
    stats_major = any(any(k in t for k in ("statistic", "p-value", "confidence interval", "multiplicity", "model specification", "uncertainty", "effect size")) for t in texts)
    robustness_major = any(any(k in t for k in ("robust", "sensitivity", "baseline", "validation", "generaliz", "replicat")) for t in texts)

    specialist_families = {
        str(v.get("specialist") or "")
        for v in (state.specialist_results or {}).values()
        if isinstance(v, dict)
    }
    claims = [c for c in state.claims if isinstance(c, dict)]
    novelty_claims = [c for c in claims if _claim_is_novelty_or_sota(c)]
    empirical = any(x in str(state.classification).lower() for x in ("empirical", "experimental", "observational", "cohort", "trial", "case-control"))
    quantitative = _quantitative_density_trigger(state)
    repro = state.reproducibility_report or {}
    env = repro.get("environment") or {}
    has_code = bool(repro.get("has_code"))

    def gate(status: str, basis: str, assessed_by: list[str]) -> dict[str, Any]:
        return {"status": status, "basis": basis, "assessed_by": assessed_by}

    if novelty_major:
        novelty_gate = gate("FAIL", "A verified novelty/prior-art barrier survived independent verification.", ["literature_search", "independent_verifier"])
    elif novelty_claims and state.literature_status.get("status") == "available":
        novelty_gate = gate("NO_VERIFIED_BARRIER", "Central novelty/SOTA claims received external search coverage and no major novelty barrier survived.", ["literature_search"])
    elif novelty_claims and state.literature_status.get("status") in {"unavailable", "insufficient", "disabled"}:
        novelty_gate = gate("CONDITIONAL", "Novelty is material, but external literature evidence was unavailable or insufficient.", ["core_review"])
    elif novelty_claims:
        novelty_gate = gate("NOT_ASSESSED", "Novelty claims were identified but did not receive adequate external assessment.", ["core_review"])
    else:
        novelty_gate = gate("N/A", "No central novelty/SOTA claim required a dedicated novelty gate.", [])

    if methods_major:
        methods_gate = gate("FAIL", "A verified major concern materially implicates design/method validity.", ["independent_verifier"])
    elif specialist_families & {"methods", "rct_intervention", "observational_epidemiology", "diagnostic_prognostic", "measurement_instrument"}:
        methods_gate = gate("NO_VERIFIED_BARRIER", "Targeted methodological review ran and no major method barrier survived verification.", sorted(specialist_families & {"methods","rct_intervention","observational_epidemiology","diagnostic_prognostic","measurement_instrument"}))
    elif empirical:
        methods_gate = gate("NOT_ASSESSED", "The manuscript is empirical, but no targeted methodological specialist completed a review.", ["core_review"])
    else:
        methods_gate = gate("N/A", "A dedicated empirical-method validity gate was not applicable.", [])

    if stats_major:
        stats_gate = gate("FAIL", "A verified major concern materially implicates statistical inference.", ["independent_verifier"])
    elif "statistics_causal" in specialist_families or "numerical" in specialist_families:
        stats_gate = gate("NO_VERIFIED_BARRIER", "Targeted statistical/numerical review ran and no major statistical barrier survived verification.", sorted(specialist for specialist in specialist_families if specialist in {"statistics_causal","numerical"}))
    elif quantitative:
        stats_gate = gate("NOT_ASSESSED", "The manuscript is quantitatively dense, but no targeted statistical/numerical specialist completed review.", ["core_review"])
    else:
        stats_gate = gate("N/A", "A dedicated statistical-validity gate was not applicable from the supplied manuscript profile.", [])

    if robustness_major:
        robustness_gate = gate("FAIL", "A verified major concern materially implicates robustness/validation/generalization.", ["independent_verifier"])
    elif specialist_families & {"computational", "reproducibility"}:
        robustness_gate = gate("NO_VERIFIED_BARRIER", "Targeted robustness/computational review ran and no major robustness barrier survived.", sorted(specialist_families & {"computational","reproducibility"}))
    elif empirical or quantitative:
        robustness_gate = gate("NOT_ASSESSED", "No dedicated robustness/validation specialist evidence was available.", ["core_review"])
    else:
        robustness_gate = gate("N/A", "A dedicated robustness/validation gate was not applicable.", [])

    if has_code and not env.get("reproducible_environment_declared"):
        repro_gate = gate("CONDITIONAL", "Code was supplied without a declared reproducible environment.", ["reproducibility_audit"])
    elif repro:
        repro_gate = gate("NO_VERIFIED_BARRIER", "No deterministic reproducibility blocker was detected in the supplied package.", ["reproducibility_audit"])
    else:
        repro_gate = gate("NOT_ASSESSED", "No reproducibility audit evidence was available.", [])

    evidence_gate = (
        gate("FAIL", f"{len(admitted)} independently verified major concern(s) remain.", ["hard_evidence_gate", "independent_verifier"])
        if has_major else
        gate("CONDITIONAL", "No major concern survived, but material uncertainty remains in the frozen core review.", ["core_review", "independent_verifier"])
        if uncertainty else
        gate("NO_VERIFIED_BARRIER", "No major claim/evidence failure survived the evidence-locked independent verifier.", ["hard_evidence_gate", "independent_verifier"])
    )

    return {
        "contribution_novelty": novelty_gate,
        "evidence_adequacy": evidence_gate,
        "methodological_validity": methods_gate,
        "statistical_validity": stats_gate,
        "robustness_validation": robustness_gate,
        "reproducibility_integrity": repro_gate,
        "claim_evidence_alignment": evidence_gate,
        "_status_semantics": {
            "FAIL": "verified material barrier",
            "CONDITIONAL": "material uncertainty or incomplete evidence",
            "NO_VERIFIED_BARRIER": "assessed; no material barrier survived verification",
            "NOT_ASSESSED": "insufficient targeted assessment to make a readiness statement",
            "N/A": "not applicable to the manuscript profile",
        },
    }


def _scorecard_evidence_bundle(state: ReviewState) -> dict[str, Any]:
    """Compact, frozen evidence bundle for 50-dimension scoring."""
    specialist = {}
    for task_id, row in (state.specialist_results or {}).items():
        if not isinstance(row, dict):
            continue
        result = row.get("result") or {}
        specialist[task_id] = {
            "specialist": row.get("specialist"),
            "candidate_concerns": [
                {
                    "title": c.get("title"),
                    "severity": c.get("severity"),
                    "claim_ids": c.get("claim_ids"),
                    "failure_mechanism": c.get("failure_mechanism"),
                    "scientific_consequence": c.get("scientific_consequence"),
                }
                for c in (result.get("candidate_concerns") or [])[:8] if isinstance(c, dict)
            ],
            "notes": list(result.get("notes") or [])[:12],
            "uncertainties": list(result.get("uncertainties") or [])[:12],
        }
    anchors = [
        {
            "anchor_id": a.get("anchor_id"), "source_type": a.get("source_type"),
            "locator": a.get("locator"), "quote_or_fact": str(a.get("quote_or_fact") or "")[:700],
            "supports": a.get("supports"),
        }
        for a in (state.evidence_anchors or [])[:80] if isinstance(a, dict)
    ]
    return {
        "classification": state.classification,
        "manuscript_digest": _compact_docs(state, max_chars=14000),
        "core_summary": {
            "manuscript_summary": (state.core_review or {}).get("manuscript_summary"),
            "strengths": (state.core_review or {}).get("strengths"),
            "remaining_uncertainties": (state.core_review or {}).get("remaining_uncertainties"),
        },
        "claims": [
            {
                "claim_id": c.get("claim_id"), "text": c.get("text"), "claim_type": c.get("claim_type"),
                "centrality": c.get("centrality"), "proof_burden": c.get("proof_burden"),
                "support_status": c.get("support_status"),
            }
            for c in (state.claims or [])[:20] if isinstance(c, dict)
        ],
        "evidence_anchors": anchors,
        "specialist_assessments": specialist,
        "literature": {
            "status": state.literature_status,
            "queries": [
                {"query": q.get("query"), "goal": q.get("goal"), "claim_ids": q.get("claim_ids"), "result_count": len(q.get("results") or [])}
                for q in (state.search_ledger or [])[:12] if isinstance(q, dict)
            ],
            "citation_metrics": state.metrics.get("citation_metrics"),
        },
        "reproducibility_audit": state.reproducibility_report,
        "reporting_audit": state.reporting_audit,
        "package_audit": state.package_audit,
        "verified_major_concerns": state.admitted_concerns,
        "rejected_concern_count": len(state.rejected_concerns or []),
        "verification_records": [
            {
                "concern_id": v.get("concern_id"), "verification_status": v.get("verification_status"),
                "verifier_status": (v.get("verdict") or {}).get("status") if isinstance(v.get("verdict"), dict) else None,
                "confidence": (v.get("verdict") or {}).get("confidence") if isinstance(v.get("verdict"), dict) else None,
            }
            for v in (state.verification_records or [])[:20] if isinstance(v, dict)
        ],
    }


def _verifier_independence(ctx) -> dict[str, Any]:
    verifier = ctx.config.verifier_model or ctx.config.model
    generator = ctx.config.strategic_model or ctx.config.model
    cross = bool(verifier and generator and verifier != generator)
    return {
        "mode": "cross-model" if cross else "fresh-context/same-model",
        "generator_model": generator,
        "verifier_model": verifier,
        "cross_model": cross,
    }


def _submission_state(state: ReviewState, benchmark: dict[str, Any] | None = None) -> dict[str, Any]:
    admitted = list(state.admitted_concerns or [])
    claim_centrality = {str(c.get("claim_id")): str(c.get("centrality") or "supporting") for c in (state.claims or []) if isinstance(c, dict)}
    central_invalidating = False
    for c in admitted:
        central = any(claim_centrality.get(str(cid)) == "central" for cid in (c.get("claim_ids") or []))
        if central and _scientific_consequence_weight(c) >= 4.0:
            central_invalidating = True
            break
    if central_invalidating:
        status = "DO_NOT_SUBMIT_YET"
        rationale = "At least one independently verified concern is claim-invalidating for a central claim."
    elif admitted:
        status = "COMPETITIVE_BUT_FIX_ADVISABLE"
        rationale = "One or more verified major concerns remain, but none was classified as central claim-invalidating."
    else:
        status = "SCIENTIFICALLY_CLEAR_FOR_EXTERNAL_REVIEW"
        rationale = "No major concern survived the evidence-locked independent-verification gate."

    if benchmark and not central_invalidating:
        frac = benchmark.get("competitive_metric_fraction")
        decision_enabled = bool(benchmark.get("decision_support_enabled"))
        if isinstance(frac, (int, float)) and benchmark.get("assessable_metrics", 0) >= 4 and decision_enabled:
            if frac >= 0.75 and not admitted:
                status = "SUBMISSION_TERRITORY"
                rationale += " The manuscript is at or above the benchmark lower-reference band on at least 75% of assessable benchmark metrics."
            elif frac >= 0.75 and admitted:
                status = "BENCHMARK_COMPETITIVE_BUT_FIX_ADVISABLE"
                rationale += " The score profile is benchmark-competitive, but verified major concern(s) remain."
        elif benchmark and not decision_enabled:
            rationale += " The supplied benchmark is reference-only for this configuration and does not change the submission state."
    return {"status": status, "rationale": rationale}


def _append_core_candidate(
    state: ReviewState,
    raw: dict[str, Any],
    *,
    source_agent: str,
    trace: dict[str, Any] | None = None,
    task_id: str | None = None,
    anchor_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    c = remap_concern_references(
        dict(raw or {}),
        claim_map=claim_alias_map(state),
        anchor_map={**anchor_alias_map(state), **(anchor_map or {})},
    )
    local = str(c.get("concern_id") or "")
    c["source_local_id"] = local or None
    c["concern_id"] = allocate_concern_id(state, source_agent=source_agent, task_id=task_id)
    c["_source_agent"] = source_agent
    if task_id:
        c["_task_id"] = task_id
    if trace:
        c["_generator"] = dict(trace)
    state.proposed_concerns.append(c)
    assert_unique_ids(state.proposed_concerns, "concern_id", "concern")
    return c


def _mode_limits(ctx) -> tuple[int, int, int]:
    if ctx.config.mode == "standard":
        return 1, min(4, int(ctx.config.literature_query_budget or 4)), 5
    if ctx.config.mode == "exhaustive":
        return min(6, int(ctx.config.specialist_limit or 6)), min(12, int(ctx.config.literature_query_budget or 12)), 10
    return min(3, int(ctx.config.specialist_limit or 3)), min(8, int(ctx.config.literature_query_budget or 8)), 8


class CoreIngestStage(Stage):
    stage_id = "C01_ingest"

    async def run(self, ctx, state):
        await IntakeStage().run(ctx, state)
        await PackageAuditStage().run(ctx, state)
        await PolicySecurityStage().run(ctx, state)
        state.mode_artifacts["pipeline"] = "core"


class CoreReviewStage(Stage):
    stage_id = "C02_core_review"

    async def run(self, ctx, state):
        system = ctx.prompts.core("CORE_REVIEWER_PROMPT.md")
        specialist_names = ", ".join(sorted(CORE_SKILL_FAMILIES))
        user = (
            _core_review_user_payload(state)
            + "\n\nRUNTIME SPECIALIST ALLOWLIST:\n" + specialist_names
            + "\n\nUse only specialist names in this allowlist. Keep the claim registry to the 5–12 scientifically important claims."
        )
        trace: dict[str, Any] = {}
        out = await _call(
            ctx,
            "core_review",
            system,
            user,
            schema=CORE_REVIEW_OUTPUT,
            model=ctx.config.strategic_model,
            agent_id="core-reviewer",
            trace_out=trace,
        )
        state.core_review = out
        state.classification = dict(out.get("classification") or {})
        state.classification["pipeline"] = "beihang-referee-core"

        state.claims = []
        state.evidence_anchors = []
        anchor_map = append_evidence_anchors(
            state,
            out.get("evidence_anchors") or [],
            source_stage="CORE",
            reviewer_id="reviewer",
        )
        claim_map = canonicalize_core_claims(state, out.get("claims") or [], anchor_map=anchor_map)
        for a in state.evidence_anchors:
            supports = [claim_map.get(x, x) for x in str(a.get("supports") or "").split(",") if x]
            a["supports"] = ",".join(supports)

        for c in out.get("candidate_concerns") or []:
            _append_core_candidate(state, c, source_agent="core-reviewer", trace=trace, anchor_map=anchor_map)

        deterministic_core_validation = _validate_core_material(state, out)
        out = _sanitize_core_auxiliary_items(state, out)
        state.core_review = out
        state.core_review_validation = {
            **deterministic_core_validation,
            "schema": "beihang-referee",
            "runtime": "beihang-referee-core",
            "core_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
            "model_verification_fields_trusted_as_proof": False,
        }
        if deterministic_core_validation.get("errors"):
            state.warnings.extend(str(x) for x in deterministic_core_validation["errors"])
        if deterministic_core_validation.get("warnings"):
            state.warnings.extend(str(x) for x in deterministic_core_validation["warnings"])

        specialist_limit, literature_limit, _ = _mode_limits(ctx)
        tasks: list[dict[str, Any]] = []
        for i, task in enumerate(out.get("specialist_requests") or [], 1):
            if not isinstance(task, dict) or task.get("specialist") not in CORE_SKILL_FAMILIES:
                continue
            row = dict(task)
            row["task_id"] = str(row.get("task_id") or f"LT{i:03d}")
            row["claim_ids"] = [claim_map.get(str(x), str(x)) for x in row.get("claim_ids") or []]
            tasks.append(row)

        # Deterministic recall safety net is merged with the model plan even
        # when the model requested some specialists. This protects against
        # incomplete routing rather than only the zero-specialist case.
        tasks.extend(_fallback_specialist_requests(state))

        # Quantitatively dense manuscripts receive a required numerical audit.
        if _quantitative_density_trigger(state) and not any(t.get("specialist") == "numerical" for t in tasks):
            tasks.append({
                "task_id": "LF-NUM",
                "specialist": "numerical",
                "claim_ids": [str(c.get("claim_id")) for c in state.claims if c.get("claim_id")][:8],
                "objective": "Audit equations, units, denominators, sample sizes, reported effects, and cross-file numerical consistency",
                "priority": "high",
                "evidence_needs": [],
                "_deterministic_required": True,
            })

        tasks = _rank_specialist_tasks(_dedupe_specialist_tasks(tasks))
        state.review_plan = tasks[:specialist_limit]

        queries: list[dict[str, Any]] = []
        for q in out.get("literature_queries") or []:
            if not isinstance(q, dict) or not str(q.get("query") or "").strip():
                continue
            row = dict(q)
            row["claim_ids"] = [claim_map.get(str(x), str(x)) for x in row.get("claim_ids") or []]
            queries.append(row)

        # Every central novelty/SOTA claim must be covered by at least one
        # bounded literature query. An unrelated query must not satisfy this gate.
        novelty_claims = [c for c in state.claims if _claim_is_novelty_or_sota(c) and str(c.get("centrality") or "central") == "central"]
        covered = {str(cid) for q in queries for cid in (q.get("claim_ids") or [])}
        for claim in novelty_claims:
            cid = str(claim.get("claim_id") or "")
            if not cid or cid in covered:
                continue
            query_text = str(claim.get("text") or "").strip()
            if query_text:
                queries.append({
                    "query": (query_text[:280] + " prior art established literature"),
                    "goal": "Verify this central novelty/prior-art claim against existing scholarly work",
                    "claim_ids": [cid],
                    "_deterministic_safety_query": True,
                })
                covered.add(cid)

        # Deduplicate search questions and prioritize deterministic novelty
        # coverage before lower-priority discretionary searches.
        seen_queries: set[str] = set()
        deduped_queries: list[dict[str, Any]] = []
        for row in sorted(queries, key=lambda q: 0 if q.get("_deterministic_safety_query") else 1):
            key = re.sub(r"\s+", " ", str(row.get("query") or "").strip().lower())
            if not key or key in seen_queries:
                continue
            seen_queries.add(key)
            deduped_queries.append(row)
        queries = deduped_queries[:literature_limit]
        state.mode_artifacts["core_literature_queries"] = queries
        state.mode_artifacts["core_trace"] = trace
        ctx.checkpoints.write_artifact("core_review.json", state.core_review)


class CoreEvidenceStage(Stage):
    stage_id = "C03_targeted_evidence"

    async def run(self, ctx, state):
        await ReportingAuditStage().run(ctx, state)
        await ReproducibilityAuditStage().run(ctx, state)

        queries = list(state.mode_artifacts.get("core_literature_queries") or [])
        if not ctx.config.enable_literature_search or not queries:
            state.literature_status = {"status": "not_requested" if not queries else "disabled", "queries": len(queries)}
            return

        if not ctx.search:
            state.search_ledger = [{**q, "results": [], "status": "search-provider-unavailable"} for q in queries]
            state.literature_status = {"status": "unavailable", "queries": len(queries), "results": 0, "opened_sources": 0}
            state.warnings.append("Core Review Pipeline requested external evidence but no search provider was available; external-evidence concerns fail closed.")
            return

        sem = asyncio.Semaphore(ctx.config.max_concurrency)

        async def one(q):
            async with sem:
                ctx.budget.consume_search()
                raw = await ctx.search.search(q.get("query", ""), limit=8)
                enriched = await asyncio.gather(*(_enrich_search_result(ctx.search, r) for r in raw[:8]))
                return {**q, "results": enriched}

        state.search_ledger = await asyncio.gather(*(one(q) for q in queries))
        state.external_evidence = [
            r for row in state.search_ledger for r in (row.get("results") or [])
            if isinstance(r, dict) and _opened_content(r)
        ]
        opened = len(state.external_evidence)
        total = sum(len(row.get("results") or []) for row in state.search_ledger)
        state.literature_status = {
            "status": "available" if opened else "insufficient",
            "queries": len(queries), "results": total, "opened_sources": opened,
        }
        ctx.checkpoints.write_artifact("core_search_ledger.json", state.search_ledger)


class CoreSpecialistStage(Stage):
    stage_id = "C04_targeted_specialists"

    async def run(self, ctx, state):
        specialist_limit, _, _ = _mode_limits(ctx)
        tasks = list(state.review_plan)[:specialist_limit]
        if not tasks:
            state.specialist_results = {}
            return
        sem = asyncio.Semaphore(ctx.config.max_concurrency)

        async def run_one(task: dict[str, Any]):
            family = str(task.get("specialist") or "")
            skills = CORE_SKILL_FAMILIES.get(family, [])
            if not skills:
                return task, {}, {}
            system = ctx.prompts.core("SPECIALIST_EXECUTOR_PROMPT.md") + "\n\n" + "\n\n".join(ctx.prompts.skill(s) for s in skills)
            claim_ids = set(task.get("claim_ids") or [])
            claims = [c for c in state.claims if not claim_ids or c.get("claim_id") in claim_ids]
            context = ContextManager(max_chars=20000).for_claims(state.document_map.get("documents", []), claims)
            user = (
                "SPECIALIST FAMILY:\n" + family
                + "\n\nTASK:\n" + json.dumps(task, ensure_ascii=False)
                + "\n\nCLAIMS:\n" + json.dumps(claims, ensure_ascii=False)[:10000]
                + "\n\nCLAIM-CENTERED MANUSCRIPT CONTEXT:\n" + context
                + "\n\nOPENED EXTERNAL EVIDENCE / SEARCH LEDGER:\n" + json.dumps(state.search_ledger, ensure_ascii=False)[:22000]
            )
            trace: dict[str, Any] = {}
            async with sem:
                out = await _call(
                    ctx,
                    f"core_specialist:{family}",
                    system,
                    user,
                    schema=CORE_SPECIALIST_RESULT,
                    agent_id=f"core-specialist-executor:{family}:{task.get('task_id')}",
                    trace_out=trace,
                )
            return task, out, trace

        results = await asyncio.gather(*(run_one(t) for t in tasks))
        for task, out, trace in results:
            family = str(task.get("specialist") or "")
            task_id = str(task.get("task_id") or family)
            state.specialist_results[task_id] = {"specialist": family, "result": out}
            if not isinstance(out, dict):
                continue
            raw_anchors = list(out.get("evidence_anchors") or [])
            if any(str(a.get("source_type") or "").lower() in {"external", "literature"} for a in raw_anchors if isinstance(a, dict)):
                raw_anchors = _materialize_literature_anchors(raw_anchors, state.search_ledger)
            anchor_map = append_evidence_anchors(
                state, raw_anchors, source_stage="CORE_SPECIALIST", reviewer_id=family, trajectory_id=task_id
            )
            for c in out.get("candidate_concerns") or []:
                _append_core_candidate(state, c, source_agent="core-specialist-executor", trace=trace, task_id=task_id, anchor_map=anchor_map)

        ctx.checkpoints.write_artifact("core_specialist_results.json", state.specialist_results)


async def _citation_verify_external(ctx, state: ReviewState) -> None:
    verifier = CitationVerifier()
    existing = {str(r.get("citation_id")) for r in state.citation_verification_records if isinstance(r, dict)}
    for a in state.evidence_anchors:
        aid = str(a.get("anchor_id") or "")
        if not aid or aid in existing or str(a.get("source_type") or "").lower() not in {"external", "literature"}:
            continue
        source_record = a.get("_matched_source_record")
        asserted = {
            "citation_id": aid,
            "source_identifier": a.get("document_id") or a.get("source_identifier"),
            "title": a.get("_matched_title") or a.get("title"),
            "year": a.get("year"),
        }
        proposition = str(a.get("quote_or_fact") or "")
        record = verifier.verify(asserted, source_record, proposition=proposition)
        if record.get("proposition_support") == "uncertain" and source_record:
            content = str(source_record.get("raw_content") or source_record.get("content") or source_record.get("text") or "")
            if content:
                schema = {
                    "type": "object", "additionalProperties": False,
                    "required": ["status", "supporting_passage", "contradicting_passage", "confidence"],
                    "properties": {
                        "status": {"enum": ["supported", "contradicted", "uncertain", "not_assessable"]},
                        "supporting_passage": {"type": "string"},
                        "contradicting_passage": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                }
                entail = await _call(
                    ctx,
                    f"core_external_entailment:{aid}",
                    "You are the Referee Core independent evidence verifier. Determine only whether the frozen source content supports the asserted proposition. Do not add claims or citations. Return strict JSON.",
                    "ASSERTED PROPOSITION:\n" + proposition + "\n\nFROZEN SOURCE CONTENT:\n" + content[:16000],
                    schema=schema,
                    model=ctx.config.verifier_model or ctx.config.model,
                    agent_id=f"core-independent-verifier:citation:{aid}",
                )
                record = verifier.verify(asserted, source_record, proposition=proposition, entailment=entail)
        state.citation_verification_records.append(record)
        existing.add(aid)
    state.metrics["citation_metrics"] = citation_metrics(state.citation_verification_records)


class CoreHardGateStage(Stage):
    stage_id = "C05_hard_evidence_gate"

    async def run(self, ctx, state):
        await _citation_verify_external(ctx, state)
        known_claims = {str(c.get("claim_id")) for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
        known_anchors = {str(a.get("anchor_id")) for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
        integrity_report = verify_anchor_integrity(state.evidence_anchors, state.document_map.get("documents", []))
        integrity = {str(r.get("anchor_id")): r for r in integrity_report.get("anchors", [])}
        citation = {str(r.get("citation_id")): r for r in state.citation_verification_records if isinstance(r, dict)}
        passed, rejected, minor = [], [], []

        # Deterministically collapse near-duplicate major concerns before they
        # consume verifier budget. Within a duplicate group, retain the most
        # evidence-rich/high-confidence formulation rather than simply the first.
        majors = [dict(x) for x in state.proposed_concerns if isinstance(x, dict) and x.get("severity") == "major"]
        duplicate_of: dict[str, str] = {}
        groups: list[list[dict[str, Any]]] = []
        for c in majors:
            text = " ".join(
                str(c.get(k) or "")
                for k in ("title", "failure_mechanism", "scientific_consequence", "minimum_resolution", "closure_criterion")
            ).lower().strip()
            claims = set(str(x) for x in (c.get("claim_ids") or []))
            placed = False
            for group in groups:
                ref = group[0]
                ref_text = " ".join(
                    str(ref.get(k) or "")
                    for k in ("title", "failure_mechanism", "scientific_consequence", "minimum_resolution", "closure_criterion")
                ).lower().strip()
                ref_claims = set(str(x) for x in (ref.get("claim_ids") or []))
                if _concerns_semantically_duplicate(c, ref):
                    group.append(c)
                    placed = True
                    break
            if not placed:
                groups.append([c])

        for group in groups:
            if len(group) <= 1:
                continue
            winner = max(
                group,
                key=lambda x: (
                    float(x.get("reviewer_confidence") or 0.0),
                    len(x.get("evidence_anchor_ids") or []),
                    len(str(x.get("failure_mechanism") or "")),
                ),
            )
            winner_id = str(winner.get("concern_id") or "")
            for item in group:
                cid = str(item.get("concern_id") or "")
                if cid and cid != winner_id:
                    duplicate_of[cid] = winner_id

        for raw in state.proposed_concerns:
            c = dict(raw)
            if c.get("severity") != "major":
                minor.append(c)
                continue
            errors: list[str] = []
            if str(c.get("concern_id") or "") in duplicate_of:
                errors.append(f"near-duplicate concern of {duplicate_of[str(c.get('concern_id') or '')]}")
            for key in ("title", "failure_mechanism", "scientific_consequence", "minimum_resolution", "closure_criterion"):
                if not str(c.get(key) or "").strip():
                    errors.append(f"{key} empty")
            claims = [str(x) for x in c.get("claim_ids") or []]
            anchors = [str(x) for x in c.get("evidence_anchor_ids") or []]
            if not claims:
                errors.append("claim_ids empty")
            if not anchors:
                errors.append("evidence_anchor_ids empty")
            unknown_claims = sorted(set(claims) - known_claims)
            unknown_anchors = sorted(set(anchors) - known_anchors)
            if unknown_claims:
                errors.append(f"unknown claims: {unknown_claims}")
            if unknown_anchors:
                errors.append(f"unknown anchors: {unknown_anchors}")
            try:
                conf = float(c.get("reviewer_confidence"))
                if conf < 0.50:
                    errors.append("reviewer_confidence below 0.50")
            except Exception:
                errors.append("reviewer_confidence invalid")
            closure = assess_closure_test(str(c.get("closure_criterion") or ""))
            if not closure.get("actionable"):
                errors.append("closure criterion failed deterministic actionability check")
            for aid in anchors:
                rec = integrity.get(aid) or {}
                if rec.get("status") not in {"verified", "external_verified"}:
                    errors.append(f"anchor failed deterministic integrity check: {aid}")
                anchor = next((a for a in state.evidence_anchors if a.get("anchor_id") == aid), {})
                if str(anchor.get("source_type") or "").lower() in {"external", "literature"}:
                    vr = citation.get(aid) or {}
                    if not (
                        vr.get("existence_status") == "verified"
                        and vr.get("metadata_status") in {"match", "partial_match"}
                        and vr.get("source_content_available") is True
                        and vr.get("proposition_support") == "supported"
                        and not vr.get("contradicting_passages")
                    ):
                        errors.append(f"external anchor lacks decisive citation verification: {aid}")

            # Prior-art / novelty accusations are impossible to establish from
            # manuscript evidence alone. Require an opened, proposition-verified
            # external scholarly anchor regardless of what the generator claimed.
            if _is_novelty_concern(c):
                external_anchor_ids = [
                    aid for aid in anchors
                    if str((next((a for a in state.evidence_anchors if a.get("anchor_id") == aid), {}) or {}).get("source_type") or "").lower()
                    in {"external", "literature"}
                ]
                if state.literature_status.get("status") != "available":
                    errors.append("novelty/prior-art concern lacks available opened scholarly evidence")
                if not external_anchor_ids:
                    errors.append("novelty/prior-art concern lacks a decisive external scholarly anchor")
                for aid in external_anchor_ids:
                    vr = citation.get(aid) or {}
                    if not (
                        vr.get("existence_status") == "verified"
                        and vr.get("metadata_status") in {"match", "partial_match"}
                        and vr.get("source_content_available") is True
                        and vr.get("proposition_support") == "supported"
                        and not vr.get("contradicting_passages")
                    ):
                        errors.append(f"novelty/prior-art external anchor not independently proposition-verified: {aid}")
            if c.get("external_verification_required") is True:
                errors.append("candidate still requires external verification")
            c["hard_gate"] = {
                "status": "passed" if not errors else "failed",
                "errors": errors,
                "closure": closure,
            }
            if errors:
                c["status"] = "rejected_at_hard_gate"
                c["admission_errors"] = errors
                rejected.append(c)
            else:
                c["status"] = "passed_hard_gate"
                passed.append(c)

        state.provenance_candidates = passed
        state.rejected_concerns.extend(rejected)
        state.mode_artifacts["core_minor_candidates"] = minor
        state.mode_artifacts["core_anchor_integrity"] = integrity_report
        ctx.checkpoints.write_artifact("core_hard_gate.json", {
            "passed": passed, "rejected": rejected, "minor_candidates": minor, "anchor_integrity": integrity_report,
        })


class CoreIndependentVerifierStage(Stage):
    stage_id = "C06_independent_verify"

    async def run(self, ctx, state):
        if not state.provenance_candidates:
            state.verification_candidates = []
            return
        claim_by_id = {c.get("claim_id"): c for c in state.claims if isinstance(c, dict)}
        anchor_by_id = {a.get("anchor_id"): a for a in state.evidence_anchors if isinstance(a, dict)}
        manuscript_sha = _manuscript_fingerprint(state)
        system = ctx.prompts.core("CORE_VERIFIER_PROMPT.md")
        sem = asyncio.Semaphore(ctx.config.max_concurrency)

        async def verify_one(c: dict[str, Any]):
            claims = [claim_by_id[x] for x in c.get("claim_ids") or [] if x in claim_by_id]
            anchors = [anchor_by_id[x] for x in c.get("evidence_anchor_ids") or [] if x in anchor_by_id]
            context = ContextManager(max_chars=16000).for_claims(state.document_map.get("documents", []), claims)
            contradiction_context = _contradiction_context(state, c, claims, max_chars=8000)
            public_candidate = _candidate_public_payload(c)
            candidate_hash = stable_json_hash(public_candidate)
            frozen = {
                "manuscript_sha256": manuscript_sha,
                "claim_registry_sha256": stable_json_hash(claims),
                "anchor_bundle_sha256": stable_json_hash(anchors),
                "candidate_sha256": candidate_hash,
            }
            user = (
                "FROZEN CANDIDATE:\n" + json.dumps(public_candidate, ensure_ascii=False)
                + "\n\nFROZEN CLAIMS:\n" + json.dumps(claims, ensure_ascii=False)
                + "\n\nFROZEN ANCHORS:\n" + json.dumps(anchors, ensure_ascii=False)
                + "\n\nCLAIM-CENTERED MANUSCRIPT CONTEXT:\n" + context
                + "\n\nADDITIONAL MANUSCRIPT CONTRADICTION CONTEXT:\n" + contradiction_context
            )
            trace: dict[str, Any] = {}
            async with sem:
                verdict = await _call(
                    ctx,
                    f"core_verify:{c.get('concern_id')}",
                    system,
                    user,
                    schema=CORE_VERIFIER,
                    model=ctx.config.verifier_model or ctx.config.model,
                    agent_id=f"core-independent-verifier:{c.get('concern_id')}",
                    trace_out=trace,
                )
            generator = c.get("_generator") or {}
            post_errors: list[str] = []
            if generator.get("context_id") and generator.get("context_id") == trace.get("context_id"):
                post_errors.append("verifier context is not independent from generator context")
            if generator.get("agent_id") and generator.get("agent_id") == trace.get("agent_id"):
                post_errors.append("verifier identity is not independent from generator identity")

            ent = verdict.get("entailment") or {}
            required = (
                "claim_mapping_valid", "anchors_support_failure_mechanism",
                "scientific_consequence_proportionate", "minimum_resolution_sufficient",
                "closure_criterion_testable", "steelman_survival_supported",
            )
            verified_major = verdict.get("status") == "verified" and verdict.get("severity") == "major"
            if verified_major:
                for key in required:
                    if ent.get(key) is not True:
                        post_errors.append(f"independent verifier did not affirm {key}")
                if ent.get("manuscript_contradiction_found") is not False:
                    post_errors.append("independent verifier found or could not exclude manuscript contradiction")
                if verdict.get("steelman_survives") is not True:
                    post_errors.append("candidate did not survive independent steelman")

            final_concern = None
            status = "rejected"
            if verified_major and not post_errors:
                final_concern = {
                    "concern_id": c.get("concern_id"),
                    "title": c.get("title"),
                    "severity": "major",
                    "claim_ids": list(c.get("claim_ids") or []),
                    "evidence_anchor_ids": list(c.get("evidence_anchor_ids") or []),
                    "failure_mechanism": c.get("failure_mechanism"),
                    "scientific_consequence": c.get("scientific_consequence"),
                    "minimum_resolution": c.get("minimum_resolution"),
                    "closure_criterion": c.get("closure_criterion"),
                    "reviewer_confidence": min(float(c.get("reviewer_confidence") or 0.0), float(verdict.get("confidence") or 0.0)),
                    "steelman": verdict.get("steelman"),
                    "steelman_survives": True,
                    "steelman_survival_reason": verdict.get("steelman_survival_reason"),
                    "external_verification_required": False,
                    "uncertainties": list(dict.fromkeys(list(c.get("uncertainties") or []) + list(verdict.get("uncertainties") or []))),
                    "suggested_validation_checks": list(c.get("suggested_validation_checks") or []),
                    "status": "admitted",
                    "hard_gate": c.get("hard_gate"),
                    "_generator": generator,
                }
                errors = validate_major_comment(final_concern, set(anchor_by_id), set(claim_by_id))
                if errors:
                    post_errors.extend(errors)
                    final_concern = None
                else:
                    status = "verified"

            if final_concern is not None:
                canonical = Concern.from_dict(final_concern)
                concern_sha = stable_json_hash(canonical.scientific_payload())
            else:
                concern_sha = None
            record = {
                "concern_id": c.get("concern_id"),
                "generator_run_id": generator.get("request_id"),
                "generator_agent_id": generator.get("agent_id"),
                "generator_context_id": generator.get("context_id"),
                "generator_model": generator.get("model"),
                "verifier_run_id": trace.get("request_id"),
                "verifier_agent_id": trace.get("agent_id"),
                "verifier_context_id": trace.get("context_id"),
                "verifier_model": trace.get("model"),
                "verifier_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
                "manuscript_sha256": frozen["manuscript_sha256"],
                "claim_registry_sha256": frozen["claim_registry_sha256"],
                "anchor_bundle_sha256": frozen["anchor_bundle_sha256"],
                "candidate_sha256": frozen["candidate_sha256"],
                "concern_sha256": concern_sha,
                "verification_status": status,
                "judge_status": verdict.get("status"),
                "verdict": verdict,
                "verifier_output_sha256": stable_json_hash(verdict),
                "deterministic_postcheck": {"status": "passed" if not post_errors else "failed", "errors": post_errors},
            }
            return c, final_concern, record

        results = await asyncio.gather(*(verify_one(c) for c in state.provenance_candidates))
        admitted: list[dict[str, Any]] = []
        for candidate, final_concern, record in results:
            state.verification_records.append(record)
            verdict = record.get("verdict") or {}
            if final_concern is not None and record.get("verification_status") == "verified":
                final_concern["independent_verification"] = {
                    "verification_status": "verified",
                    "verifier_run_id": record.get("verifier_run_id"),
                    "verifier_agent_id": record.get("verifier_agent_id"),
                    "verifier_context_id": record.get("verifier_context_id"),
                    "verifier_model": record.get("verifier_model"),
                    "verifier_output_sha256": record.get("verifier_output_sha256"),
                }
                admitted.append(final_concern)
            else:
                rejected = dict(candidate)
                rejected["status"] = f"rejected_after_verification:{verdict.get('status', 'rejected')}"
                rejected["admission_errors"] = list((record.get("deterministic_postcheck") or {}).get("errors") or [])
                if verdict.get("status") == "downgrade" or verdict.get("severity") in {"minor", "observation"}:
                    state.mode_artifacts.setdefault("core_downgraded", []).append({
                        "text": candidate.get("title") + ": " + candidate.get("failure_mechanism", ""),
                        "verification_rationale": verdict.get("rationale"),
                    })
                state.rejected_concerns.append(rejected)

        _, _, max_major = _mode_limits(ctx)
        claim_centrality = {c.get("claim_id"): str(c.get("centrality") or c.get("importance") or "supporting") for c in state.claims}
        weight = {"central": 3.0, "supporting": 2.0, "peripheral": 1.0}
        def score(c):
            cent = max((weight.get(claim_centrality.get(x, "supporting"), 2.0) for x in c.get("claim_ids") or []), default=1.0)
            consequence = _scientific_consequence_weight(c)
            return cent * consequence * float(c.get("reviewer_confidence") or 0.0)
        admitted.sort(key=score, reverse=True)
        state.priority_ranking = [{
            "concern_id": c.get("concern_id"),
            "score": score(c),
            "consequence_weight": _scientific_consequence_weight(c),
            "method": "deterministic-centrality-x-consequence-x-confidence",
        } for c in admitted]
        state.admitted_concerns = admitted[:max_major]
        state.verification_candidates = list(state.admitted_concerns)
        ctx.checkpoints.write_artifact("core_independent_verification.json", state.verification_records)


class CoreFinalizeStage(Stage):
    stage_id = "C07_finalize"

    async def run(self, ctx, state):
        await ProvenanceAuditStage().run(ctx, state)
        core = state.core_review or {}
        minor = []
        for item in core.get("minor_concerns") or []:
            if isinstance(item, str):
                minor.append(item)
            elif isinstance(item, dict):
                minor.append(item.get("text") or item.get("issue") or item.get("title") or str(item))
        for c in state.mode_artifacts.get("core_minor_candidates") or []:
            minor.append(str(c.get("title") or "Minor concern") + ": " + str(c.get("failure_mechanism") or ""))
        for item in state.mode_artifacts.get("core_downgraded") or []:
            minor.append(item)
        minor = minor[: ctx.config.max_minor_comments]
        strengths = core.get("strengths") or []
        summary = core.get("manuscript_summary") or {}
        confidence = core.get("overall_scientific_confidence")
        has_major = bool(state.admitted_concerns)
        verifier_independence = _verifier_independence(ctx)
        process_gates = {
            "evidence_lock": {"status": "pass", "admitted_major_concerns": len(state.admitted_concerns)},
            "independent_verification": {
                "status": "pass_cross_model" if verifier_independence.get("cross_model") else "pass_fresh_context_same_model",
                "verified_records": sum(r.get("verification_status") == "verified" for r in state.verification_records),
                "independence": verifier_independence,
            },
            "external_evidence": {"status": "pass" if not any("external anchor" in str(x.get("admission_errors")) for x in state.rejected_concerns) else "warn", "opened_sources": len(state.external_evidence)},
        }
        scientific_gates = _scientific_gates(state)
        state.critical_gates = {
            "process_integrity": process_gates,
            "scientific_readiness": scientific_gates,
        }
        state.final_review = {
            "decision_brief": {
                "pipeline": "Beihang Referee Core",
                "research_question": summary.get("research_question", ""),
                "claimed_contribution": summary.get("claimed_contribution", ""),
                "developmental_stage": summary.get("developmental_stage", ""),
                "verified_major_concerns": len(state.admitted_concerns),
                "no_material_scientific_barriers": not has_major,
                "overall_scientific_confidence": confidence,
                "verifier_independence": verifier_independence,
                "scientific_state": _submission_state(state),
                "recommendation_basis": (
                    "Major scientific issues remain and require closure before the central conclusions should be treated as secure."
                    if has_major else
                    "No major concern passed the evidence-locked independent-verification gate; remaining comments are minor, uncertain, or out of scope."
                ),
            },
            "minor_comments": minor,
            "strengths": strengths,
            "limitations": list(core.get("remaining_uncertainties") or []),
            "observations": list(core.get("observations") or []),
            "priority_ranking": list(state.priority_ranking or []),
            "literature_search_status": dict(state.literature_status or {}),
            "reproducibility_status": dict(state.reproducibility_report or {}),
            "reporting_status": dict(state.reporting_audit or {}),
            "numerical_status": {
                "safety_triggered": any((v or {}).get("specialist") == "numerical" for v in state.specialist_results.values() if isinstance(v, dict)),
                "specialist_result": next(((v or {}).get("result") for v in state.specialist_results.values() if isinstance(v, dict) and (v or {}).get("specialist") == "numerical"), None),
            },
            "policy_status": dict(state.policy_status or {}),
        }

        # Exhaustive Core gets one fresh reassessment of the top verified issues,
        # not the multi-trajectory machinery of Full Audit.
        if ctx.config.mode == "exhaustive" and not verifier_independence.get("cross_model"):
            state.warnings.append("Exhaustive Core is using fresh-context verification with the same model; configure --verifier-model for cross-model verification.")
        if ctx.config.mode == "exhaustive" and ctx.config.enable_reliability_pass and state.admitted_concerns:
            reliability_system = ctx.prompts.skill("40_review_reliability_repeatability")
            state.reliability = await _call(
                ctx,
                "core_exhaustive_reliability",
                reliability_system,
                "Independently reassess only whether these already-verified major concerns remain major. Do not add new concerns. Return the reliability schema.\n\n"
                + json.dumps(state.admitted_concerns[:3], ensure_ascii=False)[:18000],
                schema=S.RELIABILITY,
                model=ctx.config.verifier_model or ctx.config.model,
                agent_id="core-exhaustive-reliability",
            )
        else:
            state.reliability = {"status": "not_run_in_core_default", "note": "Exhaustive mode performs one fresh reassessment; the full audit pipeline is available for multi-trajectory analysis."}

        # Optional diagnostic scorecard. It may summarize only the frozen review;
        # it is forbidden from creating or admitting new scientific concerns.
        if ctx.config.enable_scorecard:
            score_config = json.loads((ctx.package_root / "config" / "score_dimensions.json").read_text(encoding="utf-8"))
            dimensions = list(score_config.get("dimensions") or [])
            score_bundle = _scorecard_evidence_bundle(state)
            journal_profile = load_journal_profile(ctx.config.journal_profile) if ctx.config.journal_profile else None
            scorecard = await _call(
                ctx,
                "core_scorecard",
                ctx.prompts.core("DIAGNOSTIC_SCORECARD_PROMPT.md") + "\n\n" + ctx.prompts.core("SCORECARD.md"),
                "THE SCIENTIFIC REVIEW IS FROZEN. Score only the supplied dimensions. Do not add, upgrade, or invent concerns. "
                "Use N/A for inapplicable or insufficiently evidenced dimensions. Venue fit must be N/A unless grounded target-journal evidence is supplied.\n\n"
                "TARGET JOURNAL:\n" + str(ctx.config.target_journal or "NONE")
                + "\n\nFROZEN JOURNAL PROFILE IF SUPPLIED:\n" + json.dumps(journal_profile or {}, ensure_ascii=False)[:12000]
                + "\n\nDIMENSIONS:\n" + json.dumps(dimensions, ensure_ascii=False)
                + "\n\nSCIENTIFIC GATES:\n" + json.dumps(scientific_gates, ensure_ascii=False)
                + "\n\nDIMENSION EVIDENCE BUNDLE:\n" + json.dumps(score_bundle, ensure_ascii=False)[:52000],
                schema=CORE_SCORECARD,
                model=ctx.config.strategic_model or ctx.config.model,
                agent_id="core-scorecard",
            )
            scorecard["measurement_status"] = "diagnostic_ordinal_uncalibrated"
            scorecard["precision_warning"] = "Scores are diagnostic ordinal summaries; one-point differences are not precise measurements or acceptance probabilities."
            by_name = {str(x.get("dimension")): x for x in (scorecard.get("dimensions") or []) if isinstance(x, dict)}
            scorecard["dimensions"] = [
                by_name.get(name, {"dimension": name, "score": "N/A", "justification": "Not returned by the diagnostic scorer.", "evidence_basis": [], "confidence": 0.0})
                for name in dimensions
            ]
            state.final_review["diagnostic_scorecard"] = scorecard

        # Optional single-target journal calibration after science is frozen.
        # This does not change scientific-quality scores or concern admission.
        if ctx.config.target_journal and ctx.config.enable_journal_calibration:
            journal_profile = load_journal_profile(ctx.config.journal_profile) if ctx.config.journal_profile else None
            profile_sources = (journal_profile or {}).get("sources") or []
            calibration = await _call(
                ctx,
                "core_target_journal_calibration",
                ctx.prompts.core("TARGET_JOURNAL_CALIBRATOR_PROMPT.md"),
                "TARGET JOURNAL:\n" + str(ctx.config.target_journal)
                + "\n\nFROZEN JOURNAL PROFILE FROM OFFICIAL SOURCES IF SUPPLIED:\n" + json.dumps(journal_profile or {}, ensure_ascii=False)[:18000]
                + "\n\nCLASSIFICATION:\n" + json.dumps(state.classification, ensure_ascii=False)[:8000]
                + "\n\nFROZEN DECISION BRIEF:\n" + json.dumps(state.final_review.get("decision_brief") or {}, ensure_ascii=False)
                + "\n\nSCIENTIFIC GATES:\n" + json.dumps(scientific_gates, ensure_ascii=False)
                + "\n\nVERIFIED MAJOR CONCERNS:\n" + json.dumps(state.admitted_concerns, ensure_ascii=False)[:16000]
                + "\n\nDIAGNOSTIC SCORECARD IF AVAILABLE:\n" + json.dumps(state.final_review.get("diagnostic_scorecard") or {}, ensure_ascii=False)[:20000],
                schema=CORE_TARGET_JOURNAL,
                model=ctx.config.strategic_model or ctx.config.model,
                agent_id="core-target-journal-calibrator",
            )
            if journal_profile:
                calibration["evidence_status"] = "frozen_official_profile"
                calibration["profile_source_count"] = len(profile_sources)
            else:
                calibration["evidence_status"] = "provisional_model_prior"
                calibration["profile_source_count"] = 0
                calibration["confidence"] = min(float(calibration.get("confidence") or 0.0), 0.50)
                basis = list(calibration.get("evidence_basis") or [])
                basis.insert(0, "No frozen official journal profile was supplied; venue calibration is provisional and must not be treated as current-policy verification.")
                calibration["evidence_basis"] = basis
            state.journal_landscape = [calibration]
            state.final_review["target_journal_calibration"] = calibration

        # Optional informal benchmark comparison for personal stopping/reference
        # workflows. This is deterministic and never changes scientific concerns.
        if ctx.config.benchmark_profile:
            profile = load_benchmark_profile(ctx.config.benchmark_profile)
            if profile:
                summary_scores = scorecard_summary(
                    state.final_review.get("diagnostic_scorecard") or {},
                    state.final_review.get("target_journal_calibration") or {},
                )
                comparison = compare_to_benchmark(profile, summary_scores)
                comparison["venue_calibration_evidence_status"] = (
                    (state.final_review.get("target_journal_calibration") or {}).get("evidence_status")
                )
                comparison["scorecard_evidence_bound"] = True
                state.final_review["benchmark_comparison"] = comparison
                if comparison.get("decision_support_enabled") and state.final_review.get("diagnostic_scorecard"):
                    state.final_review["diagnostic_scorecard"]["measurement_status"] = "benchmark_referenced"
                state.final_review["submission_state"] = _submission_state(state, comparison)
        else:
            state.final_review["submission_state"] = _submission_state(state)

        state.metrics["pipeline"] = "beihang-beihang-referee"
        state.metrics["core_default_stage_count"] = 7
        state.metrics["core_reasoning_roles"] = 3
        ctx.checkpoints.write_artifact("core_final_review.json", state.final_review)


CORE_INITIAL_STAGES = [
    CoreIngestStage(),
    CoreReviewStage(),
    CoreEvidenceStage(),
    CoreSpecialistStage(),
    CoreHardGateStage(),
    CoreIndependentVerifierStage(),
    CoreFinalizeStage(),
]
