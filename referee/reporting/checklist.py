from __future__ import annotations

def heuristic_checklist(text: str, profile: dict) -> dict:
    """Broad presence/absence signals only; never claims formal compliance."""
    low = text.lower()
    items = []
    for item in profile.get("signal_checks", []):
        terms = [str(x).lower() for x in item.get("terms", [])]
        found = [t for t in terms if t in low]
        items.append({
            "id": item.get("id"),
            "label": item.get("label"),
            "status": "signal_present" if found else "not_detected",
            "matched_terms": found,
            "formal_compliance_requires_authoritative_checklist": True,
        })
    return {"profile": profile.get("name"), "items": items, "formal_compliance_assessed": False}
