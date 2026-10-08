from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(slots=True)
class CallTrace:
    request_id: str
    context_id: str
    agent_id: str
    operation: str
    model: str | None

    def to_dict(self):
        return asdict(self)
