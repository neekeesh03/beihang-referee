from __future__ import annotations
from pathlib import Path
import json
from typing import Any
from ..models import ReviewState

class CheckpointStore:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.state_dir = run_dir / "state"
        self.artifact_dir = run_dir / "artifacts"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: ReviewState, stage_id: str) -> Path:
        path = self.state_dir / f"{stage_id}.json"
        path.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        (self.run_dir / "state.json").write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def load_latest(self) -> ReviewState:
        path = self.run_dir / "state.json"
        return ReviewState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def write_artifact(self, name: str, payload: Any) -> Path:
        path = self.artifact_dir / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
