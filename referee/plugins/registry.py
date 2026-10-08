from __future__ import annotations
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

@dataclass
class PluginInfo:
    name: str
    group: str
    object: Any

class PluginRegistry:
    GROUPS = ("referee.llm", "referee.search", "referee.scholarly", "referee.stage")

    def discover(self) -> list[PluginInfo]:
        found = []
        eps = entry_points()
        for group in self.GROUPS:
            selected = eps.select(group=group) if hasattr(eps, "select") else eps.get(group, [])
            for ep in selected:
                try:
                    found.append(PluginInfo(ep.name, group, ep.load()))
                except Exception:
                    continue
        return found
