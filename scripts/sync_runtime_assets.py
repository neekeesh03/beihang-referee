from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "referee" / "_assets"

ASSET_PATHS = [
    Path("core"),
    Path("agents"),
    Path("skills"),
    Path("guidelines"),
    Path("profiles/guidelines"),
    Path("profiles/domain_packs"),
    Path("config/defaults.json"),
    Path("config/profiles"),
    Path("config/benchmark_profiles"),
    Path("config/journal_profiles"),
    Path("frontend"),
    Path("benchmark_corpus"),
    Path("schemas"),
    Path("validation"),
]


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    for rel in ASSET_PATHS:
        src = ROOT / rel
        if not src.exists():
            raise FileNotFoundError(src)
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)
    print(f"Synchronized runtime assets to {DEST}")


if __name__ == "__main__":
    main()
