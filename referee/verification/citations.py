from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Callable


def _norm(text: Any) -> str:
    s=re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()
    canon={"increased":"increase","increases":"increase","increasing":"increase","improved":"improve","improves":"improve","improving":"improve","outperformed":"outperform","outperforms":"outperform","caused":"cause","causes":"cause","associated":"associate"}
    return " ".join(canon.get(t,t) for t in s.split())


def _doi(value: Any) -> str:
    s=str(value or "").strip().lower()
    s=re.sub(r"^https?://(?:dx\.)?doi\.org/", "", s)
    return s.rstrip(" .;,)")


def _content(source: dict[str,Any]) -> str:
    return str(source.get("raw_content") or source.get("content") or source.get("text") or (source.get("fetched") or {}).get("raw_content") or (source.get("fetched") or {}).get("content") or "")


def _identifier_set(source: dict[str,Any]) -> set[str]:
    ids=set()
    for k in ("doi","pmid","arxiv_id","id","url"):
        if source.get(k): ids.add(_norm(source.get(k)))
    if source.get("doi"): ids.add(_doi(source.get("doi")))
    for v in (source.get("identifiers") or {}).values() if isinstance(source.get("identifiers"),dict) else []:
        ids.add(_norm(v)); ids.add(_doi(v))
    return {x for x in ids if x}


_NEGATION_PATTERNS=(
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bwithout\b", r"\bfailed to\b",
    r"\bdid not\b", r"\bdoes not\b", r"\bcannot\b", r"\bcan't\b", r"\bno evidence\b",
    r"\bnot associated\b", r"\bnot significant\b", r"\bwas not observed\b", r"\bwere not observed\b",
)


def _sentences(text:str)->list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _contains_negation(sentence:str)->bool:
    low=sentence.lower()
    return any(re.search(p,low) for p in _NEGATION_PATTERNS)


def _direct_quote_entailment(proposition:str, content:str)->dict[str,Any]:
    """Conservative deterministic layer.

    It may establish support only for a directly resolved proposition in a
    non-negated source sentence. Paraphrase/token overlap never establishes
    support. Contradiction cues can reject obvious opposite/negated claims.
    """
    p=_norm(proposition)
    if not p or not content:
        return {"status":"not_assessable","supporting_passage":"","contradicting_passage":"","confidence":0.0,"method":"deterministic-direct"}
    for sentence in _sentences(content):
        ns=_norm(sentence)
        if p and p in ns:
            if _contains_negation(sentence):
                return {"status":"contradicted","supporting_passage":"","contradicting_passage":sentence,"confidence":0.99,"method":"deterministic-negation"}
            return {"status":"supported","supporting_passage":sentence,"contradicting_passage":"","confidence":0.99,"method":"deterministic-direct"}
    # If the source repeats most proposition terms but explicitly negates the
    # relation, mark contradiction; otherwise lexical similarity is deliberately
    # non-decisive and remains uncertain.
    pt=set(p.split())
    for sentence in _sentences(content):
        st=set(_norm(sentence).split())
        overlap=len(pt & st)/max(1,len(pt))
        if overlap>=0.60 and _contains_negation(sentence):
            return {"status":"contradicted","supporting_passage":"","contradicting_passage":sentence,"confidence":0.9,"method":"deterministic-negation"}
    return {"status":"uncertain","supporting_passage":"","contradicting_passage":"","confidence":0.0,"method":"requires-independent-entailment"}


class CitationVerifier:
    """Independent citation/evidence verifier.

    Provenance/metadata is deterministic. Proposition support is fail-closed:
    exact non-negated quotations may be verified deterministically; paraphrased
    propositions require a separately supplied entailment decision. Token
    overlap alone can never yield ``supported``.
    """
    def verify(self, citation: dict[str,Any], source: dict[str,Any] | None, *, proposition: str="", entailment: dict[str,Any] | None=None) -> dict[str,Any]:
        citation_id=str(citation.get("citation_id") or citation.get("anchor_id") or "EXT-UNASSIGNED")
        identifier=str(citation.get("identifier") or citation.get("source_identifier") or citation.get("doi") or "")
        identifier_type="doi" if _doi(identifier).startswith("10.") else ("pmid" if str(identifier).isdigit() else "other")
        if not source:
            return {"citation_id":citation_id,"identifier_type":identifier_type,"identifier":identifier,"existence_status":"not_found" if identifier else "unverifiable","metadata_status":"unverifiable","title_match":False,"author_match":False,"year_match":False,"venue_match":False,"source_content_available":False,"proposition_support":"not_assessable","supporting_passages":[],"contradicting_passages":[],"entailment_method":"none","entailment_confidence":0.0,"verification_sources":[],"content_sha256":None,"verification_timestamp":datetime.now(timezone.utc).isoformat()}
        ids=_identifier_set(source)
        requested_id=_doi(identifier) if identifier_type=="doi" else _norm(identifier)
        existence="verified" if (requested_id and requested_id in ids) else ("ambiguous" if not identifier else "not_found")
        title_req=_norm(citation.get("title")); title_actual=_norm(source.get("title"))
        title_match=bool(title_req and title_actual and title_req==title_actual) if title_req else bool(title_actual)
        year_req=str(citation.get("year") or ""); year_actual=str(source.get("year") or "")
        year_match=bool(year_req and year_actual and year_req==year_actual) if year_req else bool(year_actual or source.get("provider"))
        authors_req=[_norm(x) for x in (citation.get("authors") or []) if x]
        authors_actual=[_norm(x) for x in (source.get("authors") or []) if x]
        author_match=(not authors_req) or bool(authors_actual and set(authors_req).issubset(set(authors_actual)))
        venue_req=_norm(citation.get("venue")); venue_actual=_norm(source.get("venue"))
        venue_match=(not venue_req) or bool(venue_actual and venue_req==venue_actual)
        checks=[x for requested,x in ((bool(title_req),title_match),(bool(year_req),year_match),(bool(authors_req),author_match),(bool(venue_req),venue_match)) if requested]
        if not checks: metadata="unverifiable"
        elif all(checks): metadata="match"
        elif any(checks): metadata="partial_match"
        else: metadata="mismatch"
        content=_content(source)
        ent=_direct_quote_entailment(proposition,content)
        if entailment is not None and ent["status"] not in {"supported","contradicted"}:
            status=str(entailment.get("status") or "uncertain")
            if status not in {"supported","contradicted","uncertain","not_assessable"}: status="uncertain"
            ent={
                "status":status,
                "supporting_passage":str(entailment.get("supporting_passage") or ""),
                "contradicting_passage":str(entailment.get("contradicting_passage") or ""),
                "confidence":float(entailment.get("confidence") or 0.0),
                "method":"independent-entailment",
            }
        return {"citation_id":citation_id,"identifier_type":identifier_type,"identifier":identifier,"existence_status":existence,"metadata_status":metadata,"title_match":title_match,"author_match":author_match,"year_match":year_match,"venue_match":venue_match,"source_content_available":bool(content),"proposition_support":ent["status"],"supporting_passages":[ent["supporting_passage"]] if ent.get("supporting_passage") else [],"contradicting_passages":[ent["contradicting_passage"]] if ent.get("contradicting_passage") else [],"entailment_method":ent["method"],"entailment_confidence":ent["confidence"],"verification_sources":[{"provider":source.get("provider"),"url":source.get("url"),"doi":source.get("doi")}],"content_sha256":hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None,"verification_timestamp":datetime.now(timezone.utc).isoformat()}


def decisive_external_evidence_ok(record:dict[str,Any])->bool:
    return bool(record.get("existence_status")=="verified" and record.get("metadata_status") in {"match","partial_match"} and record.get("source_content_available") and record.get("proposition_support")=="supported" and not record.get("contradicting_passages"))


def citation_metrics(records: list[dict[str,Any]]) -> dict[str,Any]:
    n=len(records)
    if not n: return {"citation_count":0,"citation_existence_accuracy":None,"citation_metadata_accuracy":None,"citation_support_accuracy":None,"fabricated_reference_rate":None,"metadata_mismatch_rate":None,"unsupported_citation_rate":None,"contradicted_citation_rate":None,"unverifiable_citation_rate":None}
    verified=sum(r.get("existence_status")=="verified" for r in records)
    metadata=sum(r.get("metadata_status")=="match" for r in records)
    support=sum(r.get("proposition_support")=="supported" for r in records)
    fabricated=sum(r.get("existence_status")=="not_found" for r in records)
    mismatch=sum(r.get("metadata_status")=="mismatch" for r in records)
    unsupported=sum(r.get("proposition_support") in {"not_supported","contradicted"} for r in records)
    contradicted=sum(r.get("proposition_support")=="contradicted" for r in records)
    unverifiable=sum(r.get("existence_status") in {"ambiguous","unverifiable"} or r.get("proposition_support") in {"not_assessable","uncertain"} for r in records)
    return {"citation_count":n,"citation_existence_accuracy":round(verified/n,4),"citation_metadata_accuracy":round(metadata/n,4),"citation_support_accuracy":round(support/n,4),"fabricated_reference_rate":round(fabricated/n,4),"metadata_mismatch_rate":round(mismatch/n,4),"unsupported_citation_rate":round(unsupported/n,4),"contradicted_citation_rate":round(contradicted/n,4),"unverifiable_citation_rate":round(unverifiable/n,4)}
