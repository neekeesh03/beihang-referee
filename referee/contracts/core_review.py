from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .concern import normalize_concern, validate_concern_contract
from ..verification.closure import assess_closure_test


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _external_keys(rows: list[dict[str, Any]] | None) -> set[str]:
    keys: set[str] = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for k in ("source_identifier", "doi", "pmid", "arxiv_id", "id", "url", "title"):
            v = row.get(k)
            if v:
                keys.add(_norm(v))
    return keys


def _concern_duplicate_key(c: dict[str, Any]) -> tuple[tuple[str, ...], str]:
    claims = tuple(sorted(str(x) for x in c.get("claim_ids", []) if x))
    core = _norm(c.get("failure_mechanism") or c.get("title"))
    return claims, core


def _near_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if set(a.get("claim_ids") or []) != set(b.get("claim_ids") or []):
        return False
    ta = _norm(a.get("failure_mechanism") or a.get("title"))
    tb = _norm(b.get("failure_mechanism") or b.get("title"))
    return bool(ta and tb and SequenceMatcher(None, ta, tb).ratio() >= 0.90)


def validate_and_materialize_core_review(
    review: dict[str, Any],
    *,
    review_mode: str,
    documents: list[dict[str, Any]],
    verified_external_evidence: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Deterministically validate model output and materialize runtime claims/anchors.

    Crucially, model-written ``verification_status`` values are ignored. Anchor
    validity is recomputed from frozen manuscript text or explicitly supplied
    verified external evidence.
    """
    errors: list[str] = []
    if review.get("review_protocol") != "beihang-referee":
        errors.append("review_protocol mismatch")
    if review.get("review_mode") != review_mode:
        errors.append(f"review_mode mismatch: expected {review_mode!r}")

    claims_raw = [x for x in review.get("claim_registry", []) if isinstance(x, dict)]
    anchors_raw = [x for x in review.get("evidence_anchors", []) if isinstance(x, dict)]
    claim_ids = [str(x.get("claim_id")) for x in claims_raw if x.get("claim_id")]
    anchor_ids = [str(x.get("anchor_id")) for x in anchors_raw if x.get("anchor_id")]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_id in claim_registry")
    if len(anchor_ids) != len(set(anchor_ids)):
        errors.append("duplicate anchor_id in evidence_anchors")
    known_claims = set(claim_ids)
    known_anchors = set(anchor_ids)

    docs = [(str(d.get("document_id") or ""), _norm(d.get("text", ""))) for d in documents]
    ext_keys = _external_keys(verified_external_evidence)
    anchor_validation: dict[str, Any] = {}
    internal_anchors: list[dict[str, Any]] = []

    # reverse link from anchors to claims, used only as runtime metadata
    anchor_to_claims: dict[str, list[str]] = {aid: [] for aid in known_anchors}
    for c in claims_raw:
        cid = c.get("claim_id")
        refs = c.get("supporting_evidence") or []
        unknown = sorted(set(refs) - known_anchors)
        if unknown:
            errors.append(f"{cid}: unknown supporting_evidence anchors {unknown}")
        for aid in refs:
            if aid in anchor_to_claims:
                anchor_to_claims[aid].append(str(cid))

    for a in anchors_raw:
        aid = str(a.get("anchor_id") or "")
        # Never trust this field as evidence of validity.
        model_status = a.get("verification_status")
        source_type = str(a.get("source_type") or "manuscript")
        fact = _norm(a.get("quote_or_fact"))
        deterministic_status = "invalid"
        document_id = ""
        matched_documents: list[str] = []
        if source_type == "manuscript":
            matched_documents = [did for did, text in docs if fact and fact in text]
            if matched_documents:
                deterministic_status = "verified"
                document_id = matched_documents[0]
            else:
                errors.append(f"{aid}: manuscript quote_or_fact not found in supplied manuscript material")
        elif source_type == "external":
            identifier = _norm(a.get("source_identifier"))
            title = _norm(a.get("title"))
            if (identifier and identifier in ext_keys) or (title and title in ext_keys):
                deterministic_status = "external_verified"
                document_id = str(a.get("source_identifier") or a.get("title") or "external")
            else:
                errors.append(f"{aid}: external anchor is not present in VERIFIED_EXTERNAL_EVIDENCE")
        else:
            errors.append(f"{aid}: unsupported source_type {source_type!r}")

        anchor_validation[aid] = {
            "status": deterministic_status,
            "model_verification_status_ignored": model_status,
            "matched_documents": matched_documents,
        }
        internal_anchors.append({
            "anchor_id": aid,
            "source_type": source_type,
            "document_id": document_id,
            "locator": str(a.get("page_or_location") or a.get("section") or ""),
            "quote_or_fact": str(a.get("quote_or_fact") or ""),
            "supports": ",".join(anchor_to_claims.get(aid, [])),
            "confidence": "high" if deterministic_status in {"verified", "external_verified"} else "low",
            "section": a.get("section"),
            "page_or_location": a.get("page_or_location"),
            "source_identifier": a.get("source_identifier"),
            "title": a.get("title"),
            "year": a.get("year"),
            "deterministic_verification_status": deterministic_status,
        })

    internal_claims: list[dict[str, Any]] = []
    importance_map = {"central": "primary", "supporting": "secondary", "peripheral": "peripheral"}
    for c in claims_raw:
        refs = list(c.get("supporting_evidence") or [])
        internal_claims.append({
            "claim_id": c.get("claim_id"),
            "text": c.get("claim_text", ""),
            "claim_text": c.get("claim_text", ""),
            "claim_type": c.get("claim_type", "other"),
            "centrality": importance_map.get(c.get("importance"), c.get("importance", "secondary")),
            "importance": c.get("importance"),
            "scope": c.get("location", ""),
            "location": c.get("location", ""),
            "proof_burden": [],
            "evidence_anchor_ids": refs,
            "supporting_evidence": refs,
            "support_status": c.get("support_strength", "unclear"),
            "support_strength": c.get("support_strength", "unclear"),
            "confidence": "unassessed",
            "alternatives": [],
        })

    majors = [normalize_concern(x) for x in review.get("major_concerns", []) if isinstance(x, dict)]
    seen_ids: set[str] = set()
    for i, c in enumerate(majors):
        cid = str(c.get("concern_id") or f"major[{i}]")
        if cid in seen_ids:
            errors.append(f"duplicate major concern id: {cid}")
        seen_ids.add(cid)
        errors.extend(f"{cid}: {e}" for e in validate_concern_contract(c, known_claim_ids=known_claims, known_anchor_ids=known_anchors))
        closure = assess_closure_test(str(c.get("closure_criterion") or ""))
        if not closure.get("actionable"):
            errors.append(f"{cid}: closure criterion is not objectively actionable/testable")
        for j in range(i):
            if _near_duplicate(c, majors[j]):
                errors.append(f"{cid}: duplicates or near-duplicates {majors[j].get('concern_id')}")
                break

    # Validate all cross-references in strengths, minor concerns and observations.
    for section in ("strengths", "minor_concerns", "observations"):
        for idx, row in enumerate(review.get(section, []) or []):
            if not isinstance(row, dict):
                continue
            cr = row.get("claim_ids") or []
            ar = row.get("anchor_ids") if section == "strengths" else row.get("evidence_anchor_ids") or []
            unknown_c = sorted(set(cr) - known_claims)
            unknown_a = sorted(set(ar) - known_anchors)
            if unknown_c:
                errors.append(f"{section}[{idx}]: unknown claim IDs {unknown_c}")
            if unknown_a:
                errors.append(f"{section}[{idx}]: unknown anchor IDs {unknown_a}")
            conf = row.get("reviewer_confidence")
            if conf is not None and (not isinstance(conf, (int, float)) or isinstance(conf, bool) or not 0 <= float(conf) <= 1):
                errors.append(f"{section}[{idx}]: reviewer_confidence outside [0,1]")

    novelty = review.get("novelty_assessment") or {}
    ext_refs = novelty.get("external_anchor_ids") or []
    if any(x not in known_anchors for x in ext_refs):
        errors.append("novelty_assessment references unknown external anchors")
    if novelty.get("status") in {"supported", "questioned"}:
        if not ext_refs or any(anchor_validation.get(x, {}).get("status") != "external_verified" for x in ext_refs):
            errors.append("decisive novelty assessment lacks deterministically verified external evidence")

    numerical = review.get("numerical_consistency") or {}
    numerical_issues = numerical.get("issues") or []
    if numerical.get("status") == "consistent" and numerical_issues:
        errors.append("numerical_consistency is 'consistent' but issues are listed")
    if numerical.get("status") == "issues_found" and not numerical_issues:
        errors.append("numerical_consistency is 'issues_found' but issues array is empty")

    summary = review.get("review_summary") or {}
    supported_ids = set(summary.get("central_claims_supported") or [])
    risk_ids = set(summary.get("central_claims_at_risk") or [])
    overlap = sorted(supported_ids & risk_ids)
    if overlap:
        errors.append(f"review_summary marks the same central claims both supported and at risk: {overlap}")
    for key in ("central_claims_supported", "central_claims_at_risk"):
        unknown = sorted(set(summary.get(key) or []) - known_claims)
        if unknown:
            errors.append(f"review_summary.{key}: unknown claim IDs {unknown}")
    unknown_mc = sorted(set(summary.get("strongest_concern_ids") or []) - seen_ids)
    if unknown_mc:
        errors.append(f"review_summary.strongest_concern_ids: unknown concern IDs {unknown_mc}")

    audit = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "claim_count": len(internal_claims),
        "anchor_count": len(internal_anchors),
        "anchor_validation": anchor_validation,
        "model_verification_status_trusted": False,
    }
    return errors, internal_claims, internal_anchors, audit
