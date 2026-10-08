from __future__ import annotations
import re
from typing import Any

class ContextManager:
    """Builds bounded claim-centered context without requiring embeddings.

    This is deliberately deterministic. Hosts can replace it with vector retrieval,
    but the runtime always preserves stable document/locator provenance.
    """
    def __init__(self, max_chars: int = 18000, window: int = 1200):
        self.max_chars = max_chars
        self.window = window

    def for_claims(self, documents: list[dict[str, Any]], claims: list[dict[str, Any]]) -> str:
        terms = []
        for c in claims:
            words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", str(c.get("text", "")))
            terms.extend(words[:8])
        terms = list(dict.fromkeys(t.lower() for t in terms))[:30]
        chunks = []
        used = 0
        for d in documents:
            text = d.get("text", "")
            spans = []
            lower = text.lower()
            for term in terms:
                pos = lower.find(term)
                if pos >= 0:
                    spans.append((max(0, pos-self.window), min(len(text), pos+self.window)))
            if not spans:
                spans = [(0, min(len(text), 2500))]
            for start, end in spans[:4]:
                piece = text[start:end]
                if used + len(piece) > self.max_chars:
                    piece = piece[: max(0, self.max_chars-used)]
                if not piece:
                    break
                chunks.append(f"### {d.get('document_id')} chars {start}-{start+len(piece)}\n{piece}")
                used += len(piece)
                if used >= self.max_chars:
                    return "\n\n".join(chunks)
        return "\n\n".join(chunks)
