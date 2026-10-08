from __future__ import annotations

import re
from typing import Any

_KIND_PREFIX = {"claim": "C", "anchor": "A", "concern": "MC", "verification": "V", "external": "EXT"}


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "RUNTIME")).strip("-").upper()
    return text[:32] or "RUNTIME"


def _next(existing: set[str], kind: str, source: str) -> str:
    prefix = _KIND_PREFIX[kind]
    stem = f"{prefix}-{_slug(source)}-"
    nums = []
    for item in existing:
        if item.startswith(stem):
            tail = item[len(stem):]
            if tail.isdigit():
                nums.append(int(tail))
    return f"{stem}{max(nums, default=0)+1:04d}"


def assert_unique_ids(rows: list[dict[str, Any]], key: str, label: str) -> None:
    ids = [str(r.get(key)) for r in rows if isinstance(r, dict) and r.get(key)]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate canonical {label} ID")


def append_evidence_anchors(state, anchors: list[dict[str, Any]] | None, *, source_stage: str,
                            reviewer_id: str | None = None, trajectory_id: str | None = None) -> dict[str, str]:
    """Register model anchors under runtime-owned globally unique IDs.

    The model's anchor_id is retained as source_local_id only. Concerns from the
    same stage must be remapped with the returned local->canonical mapping.
    """
    rows = [dict(a) for a in (anchors or []) if isinstance(a, dict)]
    locals_ = [str(a.get("anchor_id") or "") for a in rows]
    nonempty = [x for x in locals_ if x]
    if len(nonempty) != len(set(nonempty)):
        raise ValueError("duplicate local anchor IDs within one stage output")
    existing = {str(a.get("anchor_id")) for a in state.evidence_anchors if isinstance(a, dict) and a.get("anchor_id")}
    source = source_stage
    if reviewer_id:
        source += f"-{reviewer_id}"
    if trajectory_id:
        source += f"-{trajectory_id}"
    mapping: dict[str, str] = {}
    for row in rows:
        local = str(row.get("anchor_id") or "")
        canonical = _next(existing, "anchor", source)
        if canonical in existing:
            raise ValueError(f"duplicate canonical anchor insertion: {canonical}")
        existing.add(canonical)
        if local:
            mapping[local] = canonical
        row["source_local_id"] = local or None
        row["anchor_id"] = canonical
        row["source_stage"] = source_stage
        if reviewer_id:
            row["reviewer_id"] = reviewer_id
        if trajectory_id:
            row["trajectory_id"] = trajectory_id
        state.evidence_anchors.append(row)
    assert_unique_ids(state.evidence_anchors, "anchor_id", "anchor")
    return mapping


def canonicalize_core_claims(state, claims: list[dict[str, Any]], *, anchor_map: dict[str, str]) -> dict[str, str]:
    rows = [dict(c) for c in claims if isinstance(c, dict)]
    local_ids = [str(c.get("claim_id") or "") for c in rows]
    nonempty = [x for x in local_ids if x]
    if len(nonempty) != len(set(nonempty)):
        raise ValueError("duplicate local claim IDs in core review")
    existing = {str(c.get("claim_id")) for c in state.claims if isinstance(c, dict) and c.get("claim_id")}
    mapping: dict[str, str] = {}
    for row in rows:
        local = str(row.get("claim_id") or "")
        canonical = _next(existing, "claim", "CORE")
        existing.add(canonical)
        if local:
            mapping[local] = canonical
        row["source_local_id"] = local or None
        row["claim_id"] = canonical
        refs = list(row.get("evidence_anchor_ids") or row.get("supporting_evidence") or [])
        refs = [anchor_map.get(str(x), str(x)) for x in refs]
        row["evidence_anchor_ids"] = refs
        if "supporting_evidence" in row:
            row["supporting_evidence"] = refs
        state.claims.append(row)
    assert_unique_ids(state.claims, "claim_id", "claim")
    return mapping


def claim_alias_map(state) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in state.claims:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("claim_id") or "")
        if cid:
            out[cid] = cid
        local = str(c.get("source_local_id") or "")
        if local:
            # Claims currently originate from the authoritative core registry;
            # if that changes, aliases must become source-scoped instead.
            out.setdefault(local, cid)
    return out


def anchor_alias_map(state) -> dict[str, str]:
    out: dict[str,str] = {}
    for a in state.evidence_anchors:
        if not isinstance(a,dict): continue
        aid=str(a.get("anchor_id") or "")
        if aid: out[aid]=aid
        local=str(a.get("source_local_id") or "")
        if local: out.setdefault(local,aid)
    return out

def remap_concern_references(raw: dict[str, Any], *, claim_map: dict[str, str] | None = None,
                             anchor_map: dict[str, str] | None = None) -> dict[str, Any]:
    c = dict(raw or {})
    cm = claim_map or {}
    am = anchor_map or {}
    c["claim_ids"] = [cm.get(str(x), str(x)) for x in (c.get("claim_ids") or [])]
    c["evidence_anchor_ids"] = [am.get(str(x), str(x)) for x in (c.get("evidence_anchor_ids") or c.get("evidence_anchors") or [])]
    c.pop("evidence_anchors", None)
    return c


def allocate_concern_id(state, *, source_agent: str, task_id: str | None = None) -> str:
    existing = {str(c.get("concern_id")) for c in state.proposed_concerns if isinstance(c, dict) and c.get("concern_id")}
    source = source_agent + (f"-{task_id}" if task_id else "")
    cid = _next(existing, "concern", source)
    if cid in existing:
        raise ValueError(f"duplicate canonical concern insertion: {cid}")
    return cid


def validate_global_uniqueness(state_dict: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for rows_key, id_key, label in (
        ("claims", "claim_id", "claim"),
        ("evidence_anchors", "anchor_id", "anchor"),
        ("proposed_concerns", "concern_id", "proposed concern"),
        ("admitted_concerns", "concern_id", "admitted concern"),
    ):
        rows = state_dict.get(rows_key, []) or []
        ids = [str(r.get(id_key)) for r in rows if isinstance(r, dict) and r.get(id_key)]
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate canonical {label} IDs")
    return errors
