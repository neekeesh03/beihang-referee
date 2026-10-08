import json
from pathlib import Path
import pytest
from referee.models import ReviewState
from referee.validation.adversarial import run_adversarial_integrity_suite
from referee.validation.invariants import evaluate_state_invariants
from referee.finalization.bundle import freeze_run

def test_adversarial_integrity_suite_has_all_43_cases_and_all_pass():
    r=run_adversarial_integrity_suite(Path(__file__).resolve().parents[2])
    assert r["total"] == 43 and r["passed"] == 43 and r["all_critical_pass"]

def test_failed_validation_run_cannot_be_frozen(tmp_path):
    run=tmp_path/"run";run.mkdir();state=ReviewState(run_id="run",query="q",manuscript_paths=["x"],mode="deep",status="failed_validation",final_review_exportable=False)
    (run/"state.json").write_text(json.dumps(state.to_dict()),encoding="utf-8")
    with pytest.raises(ValueError): freeze_run(run)

def test_duplicate_anchor_is_hard_invariant():
    s=ReviewState(run_id="r",query="q",manuscript_paths=["x"],mode="deep").to_dict();s["evidence_anchors"]=[{"anchor_id":"A-X-0001"},{"anchor_id":"A-X-0001"}]
    r=evaluate_state_invariants(s)
    assert any(x["code"]=="DUPLICATE_CANONICAL_ANCHOR_ID" for x in r["hard_invariant_failures"])
    assert r["final_review_exportable"] is False
