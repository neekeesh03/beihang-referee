from __future__ import annotations

from pathlib import Path


def resource_root() -> Path:
    """Return the root containing Referee's runtime scientific assets.

    In a source checkout, the human-readable asset directories live at the
    repository root. Wheels also bundle a synchronized copy under
    ``referee/_assets`` so installed distributions retain the full scientific
    control plane.
    """
    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / "core").is_dir() and (repo_root / "skills").is_dir():
        return repo_root
    bundled = Path(__file__).resolve().parent / "_assets"
    if (bundled / "core").is_dir() and (bundled / "skills").is_dir():
        return bundled
    raise RuntimeError("Referee runtime assets are missing from this installation")
