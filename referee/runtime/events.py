from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Callable

@dataclass(slots=True)
class Event:
    type: str
    run_id: str
    stage: str | None
    message: str
    data: dict[str, Any]
    ts: str

class EventBus:
    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path
        self._listeners: list[Callable[[Event], None]] = []
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._listeners.append(fn)

    def emit(self, *, type: str, run_id: str, stage: str | None, message: str, data: dict[str, Any] | None = None) -> Event:
        event = Event(type, run_id, stage, message, data or {}, datetime.now(timezone.utc).isoformat())
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        for fn in self._listeners:
            fn(event)
        return event
