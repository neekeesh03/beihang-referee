from __future__ import annotations
import json
from pathlib import Path

class GuidelineRegistry:
    """Loads routing profiles, not copyrighted guideline text.

    Profiles tell the runtime which reporting family is relevant and what broad
    manuscript signals should be checked. Exact current checklists must be
    verified against the authoritative source during a live review.
    """
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def list(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def load(self, name: str) -> dict:
        return json.loads((self.root / f"{name}.json").read_text(encoding="utf-8"))

    def route(self, classification: dict) -> list[dict]:
        text = " ".join(map(str, classification.values())).lower()
        hits = []
        for name in self.list():
            p = self.load(name)
            triggers = [str(x).lower() for x in p.get("routing_terms", [])]
            score = sum(t in text for t in triggers)
            if score:
                hits.append({"name": name, "score": score, "profile": p})
        return sorted(hits, key=lambda x: x["score"], reverse=True)
