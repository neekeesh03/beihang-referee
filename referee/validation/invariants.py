from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

from ..contracts.concern import validate_concern_contract, normalize_concern, Concern
from ..utils.hashing import stable_json_hash
from ..verification.anchors import verify_anchor_integrity
from .identifiers import validate_global_uniqueness

class InvariantSeverity(str, Enum):
    HARD="hard"
    SOFT="soft"

@dataclass(frozen=True)
class InvariantFailure:
    code:str
    severity:InvariantSeverity
    message:str
    object_id:str|None=None
    def to_dict(self):
        d=asdict(self);d["severity"]=self.severity.value;return d


def validate_major_comment(obj: dict[str, Any], known_anchor_ids: set[str], known_claim_ids: set[str] | None = None) -> list[str]:
    return validate_concern_contract(normalize_concern(obj),known_claim_ids=known_claim_ids,known_anchor_ids=known_anchor_ids)


def _manuscript_hash(state:dict[str,Any])->str:
    rows=[]
    for d in (state.get("document_map") or {}).get("documents",[]):
        rows.append({"document_id":d.get("document_id"),"sha256":(d.get("metadata") or {}).get("sha256") or stable_json_hash(d.get("text",""))})
    return stable_json_hash(rows)


def evaluate_state_invariants(state:dict[str,Any])->dict[str,Any]:
    hard:list[InvariantFailure]=[];soft:list[InvariantFailure]=[]
    def add(code,msg,obj=None,severity=InvariantSeverity.HARD):
        (hard if severity==InvariantSeverity.HARD else soft).append(InvariantFailure(code,severity,msg,obj))
    for msg in validate_global_uniqueness(state):
        code="DUPLICATE_CANONICAL_ID"
        if "claim" in msg: code="DUPLICATE_CANONICAL_CLAIM_ID"
        elif "anchor" in msg: code="DUPLICATE_CANONICAL_ANCHOR_ID"
        elif "concern" in msg: code="DUPLICATE_CANONICAL_CONCERN_ID"
        add(code,msg)
    anchors=[a for a in state.get("evidence_anchors",[]) if isinstance(a,dict)]
    claims=[c for c in state.get("claims",[]) if isinstance(c,dict)]
    verification_rows=[r for r in state.get("verification_records",[]) if isinstance(r,dict) and r.get("concern_id")]
    verification_ids=[str(r.get("concern_id")) for r in verification_rows]
    if len(verification_ids)!=len(set(verification_ids)):
        add("DUPLICATE_VERIFICATION_RECORD","multiple verification records share one canonical concern ID")
    citation_rows=[r for r in state.get("citation_verification_records",[]) if isinstance(r,dict) and r.get("citation_id")]
    citation_ids=[str(r.get("citation_id")) for r in citation_rows]
    if len(citation_ids)!=len(set(citation_ids)):
        add("DUPLICATE_CITATION_VERIFICATION_RECORD","multiple citation verification records share one canonical citation/anchor ID")
    anchor_by={a.get("anchor_id"):a for a in anchors if a.get("anchor_id")};claim_by={c.get("claim_id"):c for c in claims if c.get("claim_id")}
    verification={r.get("concern_id"):r for r in state.get("verification_records",[]) if isinstance(r,dict) and r.get("concern_id")}
    documents=(state.get("document_map") or {}).get("documents",[])
    integrity=verify_anchor_integrity(anchors,documents) if documents else {"anchors":[]}
    imap={r.get("anchor_id"):r for r in integrity.get("anchors",[])}
    citation={r.get("citation_id"):r for r in state.get("citation_verification_records",[]) if isinstance(r,dict) and r.get("citation_id")}
    mhash=_manuscript_hash(state)
    if (state.get("core_review_validation") or {}).get("status")=="failed": add("SCHEMA_INVALID_SCIENTIFIC_STATE","core review deterministic/schema validation failed")
    for c0 in state.get("admitted_concerns",[]):
        if not isinstance(c0,dict): continue
        c=normalize_concern(c0);cid=str(c.get("concern_id") or "?")
        for err in validate_major_comment(c,set(anchor_by),set(claim_by)): add("BROKEN_ADMITTED_CONCERN_REFERENCE",err,cid)
        for q in c.get("claim_ids",[]):
            if q not in claim_by:add("MISSING_CLAIM_REFERENCE",f"admitted concern references missing claim {q}",cid)
        for aid in c.get("evidence_anchor_ids",[]):
            if aid not in anchor_by:add("MISSING_ANCHOR_REFERENCE",f"admitted concern references missing anchor {aid}",cid);continue
            if documents and anchor_by[aid].get("quote_or_fact") and (imap.get(aid) or {}).get("status") not in {"verified","external_verified"}:add("INVALID_MANUSCRIPT_ANCHOR",f"admitted concern references invalid anchor {aid}",cid)
            a=anchor_by[aid]
            if str(a.get("source_type") or "").lower() in {"external","literature"}:
                vr=citation.get(aid)
                if not vr:add("EXTERNAL_EVIDENCE_PROVENANCE_MISSING",f"external decisive evidence lacks citation verification {aid}",cid)
                elif not (vr.get("existence_status")=="verified" and vr.get("metadata_status") in {"match","partial_match"} and vr.get("source_content_available") is True and vr.get("proposition_support")=="supported" and not vr.get("contradicting_passages")):
                    add("EXTERNAL_EVIDENCE_PROVENANCE_INVALID",f"external decisive evidence failed independent identity/proposition verification {aid}",cid)
        rec=verification.get(cid)
        if not rec:add("MISSING_VERIFICATION_RECORD","verification record missing for admitted major concern",cid);continue
        if rec.get("verification_status")!="verified":add("VERIFICATION_NOT_VERIFIED","admitted concern verification status is not verified",cid)
        if rec.get("generator_context_id") and rec.get("generator_context_id")==rec.get("verifier_context_id"):add("INVALID_VERIFICATION_IDENTITY_RELATIONSHIP","generator and verifier context IDs match",cid)
        if rec.get("generator_agent_id") and rec.get("generator_agent_id")==rec.get("verifier_agent_id"):add("INVALID_VERIFICATION_IDENTITY_RELATIONSHIP","generator and verifier agent IDs match",cid)
        try:
            canonical=Concern.from_dict(c);chs=[claim_by[x] for x in canonical.claim_ids];ahs=[anchor_by[x] for x in canonical.evidence_anchor_ids]
            current={"manuscript_sha256":mhash,"claim_registry_sha256":stable_json_hash(chs),"anchor_bundle_sha256":stable_json_hash(ahs),"concern_sha256":stable_json_hash(canonical.scientific_payload())}
            codes={"manuscript_sha256":"HASH_MISMATCH_MANUSCRIPT","claim_registry_sha256":"HASH_MISMATCH_CLAIM_BUNDLE","anchor_bundle_sha256":"HASH_MISMATCH_ANCHOR_BUNDLE","concern_sha256":"HASH_MISMATCH_VERIFIED_CONCERN"}
            for k,v in current.items():
                if k in rec and rec.get(k)!=v:add(codes[k],f"frozen {k} changed after verification",cid)
        except Exception as exc:add("UNRESOLVED_CANONICAL_REFERENCE_CORRUPTION",str(exc),cid)
    failed_gates=[k for k,v in (state.get("critical_gates") or {}).items() if isinstance(v,dict) and v.get("status")=="fail"]
    brief=(state.get("final_review") or {}).get("decision_brief",{})
    if failed_gates and brief.get("no_material_scientific_barriers") is True:add("DECISION_BRIEF_GATE_CONTRADICTION","decision brief contradicts failed critical gates",severity=InvariantSeverity.SOFT)
    return {"status":"failed_validation" if hard else ("completed_with_validation_warnings" if soft else "passed"),"hard_invariant_failures":[x.to_dict() for x in hard],"soft_invariant_failures":[x.to_dict() for x in soft],"final_review_exportable":not hard}


def validate_state_consistency(state:dict[str,Any])->list[str]:
    report=evaluate_state_invariants(state)
    return [x["message"] for x in report["hard_invariant_failures"]+report["soft_invariant_failures"]]
