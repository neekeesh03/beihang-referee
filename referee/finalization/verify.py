from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


def verify_handoff(path: str | Path) -> dict[str, Any]:
    """Verify the internal file hashes of a frozen Referee handoff archive."""
    path = Path(path)
    failures: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        try:
            manifest = json.loads(zf.read("handoff_manifest.json"))
        except KeyError as exc:
            raise ValueError("handoff_manifest.json is missing") from exc
        names = set(zf.namelist())
        checked = 0
        for item in manifest.get("files", []):
            rel = item.get("path", "")
            expected = item.get("sha256", "")
            if rel not in names:
                failures.append({"path": rel, "error": "missing"})
                continue
            actual = hashlib.sha256(zf.read(rel)).hexdigest()
            checked += 1
            if actual != expected:
                failures.append({"path": rel, "error": "sha256_mismatch"})
    return {
        "valid": not failures,
        "checked_files": checked,
        "failures": failures,
        "run_id": manifest.get("run_id"),
        "bundle_type": manifest.get("bundle_type"),
    }
