from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from ._resources import resource_root

NOVELTY_DIMENSIONS = [
    "Problem novelty", "Construct/phenomenon novelty", "Theoretical novelty",
    "Mechanistic novelty", "Methodological novelty", "Empirical/data/context novelty",
    "Predictive novelty", "Evidence for novelty claims",
]
METHOD_DIMENSIONS = [
    "Design-question alignment", "Sampling/population adequacy", "Measurement validity",
    "Measurement reliability", "Causal identification/confounding control",
    "Model specification", "Model validation", "Baseline/comparator fairness",
    "Robustness/sensitivity",
]

def _num(value: Any) -> float | None:
    try:
        if value in (None, "N/A", ""):
            return None
        return float(value)
    except Exception:
        return None

def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None

def load_benchmark_profile(name_or_path: str | None) -> dict[str, Any] | None:
    if not name_or_path:
        return None
    p = Path(name_or_path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    root = resource_root()
    candidates = [
        root / "config" / "benchmark_profiles" / f"{name_or_path}.json",
        root / "config" / "benchmark_profiles" / name_or_path,
    ]
    for c in candidates:
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Benchmark profile not found: {name_or_path}")

def load_journal_profile(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Journal profile not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not str(data.get("journal") or "").strip():
        raise ValueError("Journal profile requires a non-empty 'journal' field")
    sources = data.get("sources") or []
    if not isinstance(sources, list) or not sources:
        raise ValueError("Journal profile requires a non-empty 'sources' list")
    required = {"title", "url", "retrieved_at", "quote_or_fact", "source_kind"}
    for i, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            raise ValueError(f"Journal profile source {i} must be an object")
        missing = sorted(k for k in required if not str(source.get(k) or "").strip())
        if missing:
            raise ValueError(f"Journal profile source {i} missing required fields: {missing}")
        if source.get("source_kind") != "official_journal_or_publisher":
            raise ValueError(f"Journal profile source {i} must set source_kind='official_journal_or_publisher'")
    return data

def scorecard_summary(scorecard: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, float | None]:
    rows = {str(x.get("dimension")): _num(x.get("score")) for x in (scorecard.get("dimensions") or []) if isinstance(x, dict)}
    novelty = [rows.get(x) for x in NOVELTY_DIMENSIONS]
    novelty = [x for x in novelty if x is not None]
    methods = [rows.get(x) for x in METHOD_DIMENSIONS]
    methods = [x for x in methods if x is not None]
    importance = [rows.get("Importance of research problem"), rows.get("Scientific significance")]
    importance = [x for x in importance if x is not None]
    target = target or {}
    return {
        "overall_scientific_quality": rows.get("Overall scientific credibility / claim readiness"),
        "importance_impact": _num(target.get("impact_potential_score")) or _median(importance),
        "venue_fit": _num(target.get("fit_score")) or rows.get("Journal/venue scope fit (post-calibration only)"),
        "novelty": _median(novelty),
        "methodological_execution": _median(methods),
        "statistical_inferential_rigor": rows.get("Statistical rigor"),
        "publication_readiness": _num(target.get("publication_readiness_score")),
    }

def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("empty values")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs)-1)*q
    lo = int(pos)
    hi = min(lo+1, len(xs)-1)
    frac = pos-lo
    return xs[lo]*(1-frac)+xs[hi]*frac

def _percentile(values: list[float], x: float) -> float:
    if not values:
        return 0.0
    below = sum(v < x for v in values)
    equal = sum(v == x for v in values)
    return round(100.0 * (below + 0.5*equal) / len(values), 1)

def compare_to_benchmark(profile: dict[str, Any], current: dict[str, float | None]) -> dict[str, Any]:
    rows = profile.get("papers") or []
    mapping = profile.get("metrics") or {}
    out = {}
    competitive = 0
    assessable = 0
    for metric, field in mapping.items():
        vals = [_num(r.get(field)) for r in rows if isinstance(r, dict)]
        vals = [v for v in vals if v is not None]
        cur = current.get(metric)
        if cur is None or not vals:
            out[metric] = {"current": cur, "status": "not_assessable"}
            continue
        q25 = _quantile(vals, 0.25)
        med = statistics.median(vals)
        q75 = _quantile(vals, 0.75)
        assessable += 1
        if cur >= q25:
            competitive += 1
        if cur >= q75:
            status = "strong_reference"
        elif cur >= med:
            status = "at_or_above_median"
        elif cur >= q25:
            status = "within_published_reference_band"
        else:
            status = "below_lower_reference"
        out[metric] = {
            "current": round(cur, 3),
            "q25": round(q25, 3),
            "median": round(med, 3),
            "q75": round(q75, 3),
            "min": min(vals),
            "max": max(vals),
            "percentile": _percentile(vals, cur),
            "status": status,
        }
    return {
        "profile_id": profile.get("profile_id"),
        "label": profile.get("label"),
        "journal": profile.get("journal"),
        "sample_size": len(rows),
        "informal_calibration_only": bool(profile.get("informal_calibration_only", True)),
        "configuration_id": profile.get("configuration_id"),
        "strictly_comparable_to_current": bool(profile.get("strictly_comparable_to_current", False)),
        "decision_support_enabled": bool(profile.get("decision_support_enabled", False)),
        "mapping_note": profile.get("mapping_note", ""),
        "metrics": out,
        "competitive_metric_fraction": round(competitive / assessable, 3) if assessable else None,
        "assessable_metrics": assessable,
        "note": profile.get("note", ""),
    }
