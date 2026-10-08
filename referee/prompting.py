from __future__ import annotations
from pathlib import Path

class PromptLibrary:
    def __init__(self, package_root: Path):
        self.root = package_root

    def skill(self, skill_dir: str) -> str:
        p = self.root / "skills" / skill_dir / "SKILL.md"
        return p.read_text(encoding="utf-8")

    def agent(self, filename: str) -> str:
        return (self.root / "agents" / filename).read_text(encoding="utf-8")

    def core(self, filename: str) -> str:
        return (self.root / "core" / filename).read_text(encoding="utf-8")
