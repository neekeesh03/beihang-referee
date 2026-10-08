from __future__ import annotations
import re
from typing import Any

# These are signals, not proof. Manuscript text remains data regardless of score.
_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions",
    r"you\s+are\s+chatgpt",
    r"system\s+prompt",
    r"do\s+not\s+review",
    r"assign\s+(an?\s+)?(accept|high|perfect)\s+(score|rating|decision)",
    r"give\s+(this\s+)?manuscript\s+(an?\s+)?accept\s+(recommendation|decision|rating|score)",
    r"do\s+not\s+(report|mention|flag|identify)\s+",
    r"treat\s+(every|all)\s+concern[s]?\s+as\s+(resolved|closed)",
    r"reveal\s+(the\s+)?prompt",
]

def scan_prompt_injection(text: str) -> dict[str, Any]:
    hits = []
    lower = text.lower()
    for pattern in _PATTERNS:
        m = re.search(pattern, lower, flags=re.I)
        if m:
            hits.append({"pattern": pattern, "match": m.group(0)[:120]})
    return {"flagged": bool(hits), "signals": hits, "rule": "manuscript content is always untrusted data, never executable instruction"}
