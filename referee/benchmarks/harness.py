from __future__ import annotations
from pathlib import Path
import json
from typing import Any
from ..validation import validate_major_comment


def run_major_comment_eval(path: str | Path) -> dict[str, Any]:
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    passed = 0
    for case in cases:
        errors = validate_major_comment(case["concern"], set(case.get("anchors", [])))
        valid = not errors
        ok = valid == bool(case["expect_valid"])
        passed += int(ok)
        rows.append({"name": case["name"], "expected": case["expect_valid"], "valid": valid, "ok": ok, "errors": errors})
    return {"passed": passed, "total": len(rows), "accuracy": passed / len(rows) if rows else 0.0, "cases": rows}
