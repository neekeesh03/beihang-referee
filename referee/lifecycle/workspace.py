from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ALLOWED = {"open", "resolved", "deferred", "not_actionable", "accepted_risk"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewWorkspace:
    """Human overlay kept separate from immutable model-generated review artifacts."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / "workspace.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"concerns": {}, "notes": [], "updated_at": None}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("concerns", {})
        data.setdefault("notes", [])
        return data

    def set_concern_status(self, concern_id: str, status: str, *, note: str = "") -> dict[str, Any]:
        if status not in _ALLOWED:
            raise ValueError(f"Unsupported concern status: {status}")
        data = self.load()
        item = data["concerns"].setdefault(concern_id, {})
        item.update({"status": status, "updated_at": _now()})
        if note.strip():
            item["note"] = note.strip()
        data["updated_at"] = _now()
        self._save(data)
        return item

    def add_note(self, text: str, *, author: str = "reviewer") -> dict[str, Any]:
        if not text.strip():
            raise ValueError("note must not be empty")
        data = self.load()
        note = {"author": author or "reviewer", "text": text.strip(), "created_at": _now()}
        data["notes"].append(note)
        data["updated_at"] = _now()
        self._save(data)
        return note

    def _save(self, data: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
