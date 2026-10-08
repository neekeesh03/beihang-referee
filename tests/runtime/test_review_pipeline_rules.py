from pathlib import Path
import json

from referee.config import ReviewConfig
from referee.models import ReviewState
from referee.benchmarking import load_benchmark_profile, compare_to_benchmark
from referee.stages.review import (
    _dedupe_specialist_tasks, _concerns_semantically_duplicate,
    _fallback_specialist_requests, _scientific_gates,
)


def _state():
    return ReviewState(
        run_id="x", query="q", manuscript_paths=["paper.md"], mode="deep",
        classification={"design": "observational", "inference_type": "causal", "study_type": "empirical"},
        claims=[{
            "claim_id": "C001", "text": "Treatment causes improved outcome.", "claim_type": "causal",
            "centrality": "central", "proof_burden": ["causal identification"],
        }],
        document_map={"documents": [{"document_id": "D1", "text": "n=100. Accuracy 82%. 95% confidence interval. Figure 1. Table 1."}]},
    )


def test_programmatic_default_is_core():
    assert ReviewConfig().pipeline == "core"


def test_required_specialist_router_covers_incomplete_core_plan():
    state = _state()
    required = _fallback_specialist_requests(state)
    names = {x["specialist"] for x in required}
    assert "statistics_causal" in names
    assert "methods" in names
    assert all(x.get("_deterministic_required") for x in required)


def test_task_dedupe_preserves_required_safety_metadata():
    tasks = [
        {"task_id": "T1", "specialist": "statistics_causal", "claim_ids": ["C001"], "objective": "core", "priority": "medium", "evidence_needs": []},
        {"task_id": "LF1", "specialist": "statistics_causal", "claim_ids": ["C001"], "objective": "safety", "priority": "high", "evidence_needs": ["identification"], "_deterministic_required": True},
    ]
    out = _dedupe_specialist_tasks(tasks)
    assert len(out) == 1
    assert out[0]["_deterministic_required"] is True
    assert out[0]["priority"] == "high"
    assert "identification" in out[0]["evidence_needs"]


def test_semantic_duplicate_detection_allows_overlapping_claim_sets():
    a = {
        "claim_ids": ["C001"],
        "title": "Uncontrolled confounding threatens the causal conclusion",
        "failure_mechanism": "Treatment assignment is non-random and the analysis does not identify the causal effect.",
        "scientific_consequence": "The causal estimate is not identified.",
    }
    b = {
        "claim_ids": ["C001", "C002"],
        "title": "The treatment effect cannot be interpreted causally",
        "failure_mechanism": "Non-random treatment allocation leaves residual confounding in the effect estimate.",
        "scientific_consequence": "The principal causal conclusion is unsupported.",
    }
    assert _concerns_semantically_duplicate(a, b)


def test_scientific_gates_do_not_equate_no_flaw_with_pass():
    state = _state()
    state.core_review = {"remaining_uncertainties": []}
    state.reproducibility_report = {"has_code": False, "environment": {}}
    state.specialist_results = {}
    gates = _scientific_gates(state)
    statuses = {
        v.get("status") for k, v in gates.items()
        if not k.startswith("_") and isinstance(v, dict)
    }
    assert "PASS" not in statuses
    assert "NOT_ASSESSED" in statuses or "NO_VERIFIED_BARRIER" in statuses


def test_builtin_nature_benchmark_is_informal_reference():
    profile = load_benchmark_profile("nature-published")
    assert profile["journal"] == "Nature"
    assert profile["informal_calibration_only"] is True
    assert len(profile["papers"]) == 10
    current = {
        "overall_scientific_quality": 8.0,
        "importance_impact": 9.1,
        "venue_fit": 9.2,
        "novelty": 8.4,
        "methodological_execution": 8.4,
        "statistical_inferential_rigor": 6.5,
        "publication_readiness": 7.3,
    }
    comp = compare_to_benchmark(profile, current)
    assert comp["sample_size"] == 10
    assert comp["assessable_metrics"] == 7
    assert comp["metrics"]["overall_scientific_quality"]["median"] == 8.0


def test_journal_profile_requires_official_source_kind(tmp_path):
    from referee.benchmarking import load_journal_profile
    p = tmp_path / "journal.json"
    p.write_text(json.dumps({
        "journal": "X",
        "sources": [{
            "title": "Scope", "url": "https://example.org", "retrieved_at": "2026-10-07",
            "quote_or_fact": "Scope statement", "source_kind": "other"
        }]
    }))
    try:
        load_journal_profile(str(p))
    except ValueError as exc:
        assert "official_journal_or_publisher" in str(exc)
    else:
        raise AssertionError("non-official journal source should fail closed")
