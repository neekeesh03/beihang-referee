from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRegistry:
    """Small local registry for completed/in-progress review runs.

    The registry is deliberately metadata-only. Scientific state remains in each
    run directory so the registry can be deleted and rebuilt without data loss.
    """

    def __init__(self, run_root: str | Path = "runs"):
        self.run_root = Path(run_root)
        meta = self.run_root / ".referee"
        meta.mkdir(parents=True, exist_ok=True)
        self.path = meta / "registry.sqlite3"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    review_mode TEXT,
                    depth_mode TEXT,
                    query TEXT,
                    input_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    summary_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

    def upsert(
        self,
        run_id: str,
        *,
        status: str,
        review_mode: str = "",
        depth_mode: str = "",
        query: str = "",
        input_count: int = 0,
        summary: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        payload = json.dumps(summary or {}, ensure_ascii=False, sort_keys=True)
        with self._connect() as con:
            existing = con.execute("SELECT created_at FROM runs WHERE run_id=?", (run_id,)).fetchone()
            created_at = existing["created_at"] if existing else now
            con.execute(
                """
                INSERT INTO runs(run_id,status,review_mode,depth_mode,query,input_count,created_at,updated_at,summary_json)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    review_mode=excluded.review_mode,
                    depth_mode=excluded.depth_mode,
                    query=excluded.query,
                    input_count=excluded.input_count,
                    updated_at=excluded.updated_at,
                    summary_json=excluded.summary_json
                """,
                (run_id, status, review_mode, depth_mode, query, int(input_count), created_at, now, payload),
            )

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return self._row(row) if row else None

    def list(self, *, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM runs ORDER BY updated_at DESC LIMIT ?", (max(1, min(int(limit), 5000)),)
            ).fetchall()
        return [self._row(r) for r in rows]

    def rebuild(self) -> int:
        count = 0
        for run_dir in self.run_root.iterdir() if self.run_root.exists() else []:
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue
            state_path = run_dir / "state.json"
            if not state_path.exists():
                continue
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                config_path = run_dir / "config.json"
                cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
                self.upsert(
                    state.get("run_id", run_dir.name),
                    status=state.get("status", "unknown"),
                    review_mode=cfg.get("review_mode", ""),
                    depth_mode=state.get("mode", cfg.get("mode", "")),
                    query=state.get("query", ""),
                    input_count=len(state.get("manuscript_paths", [])),
                    summary={
                        "admitted_major_comments": len(state.get("admitted_concerns", [])),
                        "warnings": len(state.get("warnings", [])),
                        "specialists": len(state.get("specialist_results", {})),
                    },
                )
                count += 1
            except Exception:
                continue
        return count

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        out = dict(row)
        try:
            out["summary"] = json.loads(out.pop("summary_json"))
        except Exception:
            out["summary"] = {}
            out.pop("summary_json", None)
        return out
