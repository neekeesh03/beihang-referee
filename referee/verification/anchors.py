from __future__ import annotations
import hashlib
import re
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def verify_anchor_integrity(anchors: list[dict], documents: list[dict]) -> dict:
    """Deterministically verify that an anchor resolves to the frozen source.

    Manuscript anchors must contain a verbatim-normalized excerpt present in the
    referenced document. External anchors are only considered verified if they
    carry opened/fetched content (or an explicit content hash) and their quoted
    fact is present in that content. Snippet-only search hits never satisfy this
    gate for a decisive concern.
    """
    bydoc = {d.get("document_id"): d for d in documents}
    results: list[dict[str, Any]] = []
    for a in anchors:
        aid = a.get("anchor_id")
        source_type = str(a.get("source_type") or "manuscript").lower()
        fact = _norm(str(a.get("quote_or_fact") or ""))
        if source_type in {"manuscript", "supplement", "table", "figure", "package"}:
            doc = bydoc.get(a.get("document_id"))
            text = _norm((doc or {}).get("text", ""))
            ok = bool(doc and fact and fact in text)
            status = "verified" if ok else "invalid"
            results.append({
                "anchor_id": aid, "source_type": source_type, "document_found": bool(doc),
                "verbatim_normalized_found": ok, "status": status,
            })
            continue
        opened = a.get("raw_content") or a.get("content") or a.get("text") or (a.get("fetched") or {}).get("raw_content") or (a.get("fetched") or {}).get("content")
        content_status = a.get("content_status")
        # Never accept a model-written hash/status as proof. External decisive
        # evidence must carry opened content, and the cited quote/fact must be
        # present in that frozen content. The hash is recomputed locally.
        content_hash = hashlib.sha256(str(opened).encode("utf-8")).hexdigest() if opened else None
        supplied_hash = a.get("content_sha256")
        quote_found = bool(opened and fact and fact in _norm(str(opened)))
        ok = quote_found
        results.append({
            "anchor_id": aid, "source_type": source_type, "document_found": False,
            "content_status": content_status, "content_sha256": content_hash,
            "supplied_content_sha256_ignored": supplied_hash,
            "verbatim_normalized_found": quote_found,
            "status": "external_verified" if ok else "invalid",
        })
    return {
        "anchors": results,
        "verified": sum(r["status"] in {"verified", "external_verified"} for r in results),
        "invalid": sum(r["status"] == "invalid" for r in results),
        "total": len(results),
    }
