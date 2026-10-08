from __future__ import annotations
from dataclasses import asdict
from ..models import EvidenceAnchor
from ..contracts import Concern, validate_concern_contract

class EvidenceStore:
    def __init__(self):
        self.anchors: dict[str, EvidenceAnchor] = {}

    def add(self, anchor: EvidenceAnchor) -> None:
        if not anchor.anchor_id:
            raise ValueError("anchor_id required")
        self.anchors[anchor.anchor_id] = anchor

    def exists(self, anchor_id: str) -> bool:
        return anchor_id in self.anchors

    def validate_concern(self, concern: Concern, *, known_claim_ids: set[str] | None = None) -> list[str]:
        return validate_concern_contract(concern.to_dict(), known_claim_ids=known_claim_ids, known_anchor_ids=set(self.anchors))

    def to_list(self) -> list[dict]:
        return [asdict(v) for v in self.anchors.values()]
