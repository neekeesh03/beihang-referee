from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from .._resources import resource_root


class ProfileRegistry:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else resource_root() / "config" / "profiles"

    def names(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def get(self, name: str) -> dict[str, Any]:
        path = self.root / f"{name}.json"
        if not path.exists():
            raise KeyError(f"Unknown profile: {name}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"Invalid profile: {name}")
        return data
