from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(list(args), cwd=cwd, check=True)



def _source_files() -> list[Path]:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    paths = [ROOT / item["path"] for item in manifest.get("files", [])]
    paths += [ROOT / "MANIFEST.json", ROOT / "checksums.sha256"]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"Manifest references missing files: {missing[:5]}")
    return sorted(set(paths))


def _build_source_zip(output_dir: Path) -> Path:
    target = output_dir / "Beihang-Referee.zip"
    prefix = "Beihang-Referee"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in _source_files():
            rel = path.relative_to(ROOT).as_posix()
            zf.write(path, f"{prefix}/{rel}")
    return target


def _build_wheel(output_dir: Path) -> Path:
    wheel_dir = output_dir / "wheel"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    _run(
        sys.executable,
        "-m",
        "pip",
        "wheel",
        ".",
        "--no-deps",
        "--no-build-isolation",
        "-w",
        str(wheel_dir),
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected one wheel, found {len(wheels)}")
    final = output_dir / wheels[0].name
    shutil.move(str(wheels[0]), final)
    shutil.rmtree(wheel_dir)
    return final


def main() -> int:
    ap = argparse.ArgumentParser(description="Build validated Beihang Referee release artifacts")
    ap.add_argument("--output", default="release-dist", help="Output directory (default: release-dist)")
    ap.add_argument("--skip-validation", action="store_true", help="Development only; do not use for a public release")
    args = ap.parse_args()

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = output_dir.resolve()
    if output_dir == ROOT:
        raise SystemExit("Refusing to use the repository root as the release output directory")

    # Remove stale artifacts before rebuilding metadata so a existing output
    # directory can never leak into MANIFEST.json or the source archive.
    if output_dir.exists():
        shutil.rmtree(output_dir)

    _run(sys.executable, "scripts/rebuild_package_metadata.py")
    if not args.skip_validation:
        _run(sys.executable, "scripts/validate_package.py")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_zip = _build_source_zip(output_dir)
    wheel = _build_wheel(output_dir)

    sums = output_dir / "SHA256SUMS"
    artifacts = [source_zip, wheel]
    sums.write_text("".join(f"{_sha256(p)}  {p.name}\n" for p in artifacts), encoding="utf-8")

    print(f"Release artifacts built in {output_dir}")
    for path in [*artifacts, sums]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
