from __future__ import annotations
import json
from pathlib import Path

CORPUS_FILES = {
    "scientific": "scientific_defect_cases.jsonl",
    "domain": "domain_science_cases.jsonl",
    "revision": "revision_pairs.jsonl",
    "rebuttal": "rebuttal_cases.jsonl",
    "severity": "severity_calibration_cases.jsonl",
}


def corpus_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root)
    source = Path(__file__).resolve().parents[2] / "benchmark_corpus"
    if source.is_dir():
        return source
    from .._resources import resource_root
    bundled = resource_root() / "benchmark_corpus"
    if bundled.is_dir():
        return bundled
    raise RuntimeError("Referee benchmark corpus is missing from this installation")


def load_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def _gold_map(root: Path) -> dict[str,dict]:
    p=root/"structured_gold.jsonl"
    if not p.exists(): return {}
    return {str(x["case_id"]):x for x in load_jsonl(p)}


def load_corpus(name: str, root: str | Path | None = None) -> list[dict]:
    if name not in CORPUS_FILES:
        raise KeyError(name)
    r=corpus_root(root)
    rows=load_jsonl(r / CORPUS_FILES[name])
    if name in {"scientific","domain"}:
        gm=_gold_map(r)
        for row in rows:
            if row.get("case_id") in gm:
                row["structured_gold"]=gm[row["case_id"]]
    return rows


def all_case_count(root: str | Path | None = None) -> int:
    return sum(len(load_corpus(name, root)) for name in CORPUS_FILES)
