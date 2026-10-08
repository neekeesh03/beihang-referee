from __future__ import annotations
from typing import Any

def _q(s: Any) -> str:
    return str(s).replace('"', '\\"').replace('\n', ' ')[:120]

def build_evidence_graph_dot(state: dict[str, Any]) -> str:
    """Render claim→evidence→concern→closure relationships as Graphviz DOT."""
    lines = ["digraph PeerReviewEvidence {", "rankdir=LR;", 'node [shape=box];']
    for c in state.get("claims", []):
        cid = c.get("claim_id")
        if cid:
            lines.append(f'"{cid}" [label="{_q(cid)}: {_q(c.get("text",""))}", shape=ellipse];')
    for a in state.get("evidence_anchors", []):
        aid = a.get("anchor_id")
        if aid:
            lines.append(f'"{aid}" [label="{_q(aid)}: {_q(a.get("locator",""))}", shape=note];')
            supports = a.get("supports")
            if supports:
                if isinstance(supports, list):
                    for cid in supports:
                        lines.append(f'"{aid}" -> "{_q(cid)}" [label="supports"];')
                else:
                    lines.append(f'"{aid}" -> "{_q(supports)}" [label="supports"];')
    for concern in state.get("admitted_concerns", []):
        mid = concern.get("concern_id")
        if not mid:
            continue
        lines.append(f'"{mid}" [label="{_q(mid)}: {_q(concern.get("title",""))}", shape=diamond];')
        for cid in concern.get("claim_ids", []):
            lines.append(f'"{mid}" -> "{_q(cid)}" [label="challenges"];')
        for aid in concern.get("evidence_anchor_ids", []):
            lines.append(f'"{_q(aid)}" -> "{mid}" [label="grounds"];')
        closure = f"{mid}_closure"
        lines.append(f'"{closure}" [label="Closure: {_q(concern.get("closure_criterion",""))}", shape=component];')
        lines.append(f'"{mid}" -> "{closure}" [label="closed by"];')
    lines.append("}")
    return "\n".join(lines)
