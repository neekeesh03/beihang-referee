from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .quality import build_quality_snapshot
from ..lifecycle import ReviewWorkspace


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _closure_csv(state: dict[str, Any], workspace: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["concern_id", "severity", "title", "closure_criterion", "human_status", "human_note"])
    for c in state.get("admitted_concerns", []):
        human = workspace.get("concerns", {}).get(c.get("concern_id", ""), {})
        w.writerow([
            c.get("concern_id", ""), c.get("severity", ""), c.get("title", ""),
            c.get("closure_criterion", ""), human.get("status", "open"), human.get("note", ""),
        ])
    return buf.getvalue()


def freeze_run(run_dir: str | Path) -> dict[str, Any]:
    """Freeze a completed run into a checksum-verifiable handoff bundle.

    The handoff is a snapshot; it never mutates scientific state. Human notes live
    in workspace.json and are copied into the bundle as an overlay.
    """
    run_dir = Path(run_dir)
    state_path = run_dir / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"Missing run state: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not str(state.get("status", "")).startswith("completed"):
        raise ValueError("Only completed runs can be frozen")
    if state.get("final_review_exportable") is False or state.get("hard_invariant_failures"):
        raise ValueError("Scientifically invalid runs cannot be frozen or exported as successful review handoffs")

    workspace = ReviewWorkspace(run_dir).load()
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(exist_ok=True)
    quality = build_quality_snapshot(state, workspace)
    quality_path = artifact_dir / "quality_snapshot.json"
    quality_path.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    closure_path = artifact_dir / "closure_matrix.csv"
    closure_path.write_text(_closure_csv(state, workspace), encoding="utf-8")

    candidates: list[tuple[Path, str]] = []
    for name in ("state.json", "config.json", "inputs.json", "events.jsonl", "workspace.json"):
        p = run_dir / name
        if p.exists():
            candidates.append((p, name))
    for p in sorted(artifact_dir.iterdir()):
        if p.is_file() and p.name not in {"handoff_manifest.json", "referee-handoff.zip"}:
            candidates.append((p, f"artifacts/{p.name}"))

    manifest_files = [
        {"path": arc, "bytes": p.stat().st_size, "sha256": _sha256(p)} for p, arc in candidates
    ]
    manifest = {
        "bundle_type": "peer_review_handoff",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": state.get("run_id", run_dir.name),
        "status": state.get("status"),
        "quality_snapshot": quality,
        "files": manifest_files,
    }
    manifest_path = artifact_dir / "handoff_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    zip_path = artifact_dir / "referee-handoff.zip"
    readme = (
        "Referee review handoff\n\n"
        "This archive is a frozen snapshot of a completed review run.\n"
        "handoff_manifest.json contains SHA-256 hashes for every included file.\n"
        "workspace.json contains human review notes/statuses and is separate from model-generated state.\n"
    )
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("HANDOFF_README.txt", readme)
        zf.write(manifest_path, "handoff_manifest.json")
        for p, arc in candidates:
            zf.write(p, arc)
    return {"bundle": str(zip_path), "manifest": str(manifest_path), "files": len(candidates), "quality": quality}
