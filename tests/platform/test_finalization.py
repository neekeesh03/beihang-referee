import json
import zipfile
from referee.finalization import freeze_run
from referee.lifecycle import ReviewWorkspace


def test_freeze_run_builds_verifiable_handoff(tmp_path):
    run = tmp_path / "r1"; artifacts = run / "artifacts"; artifacts.mkdir(parents=True)
    state = {
        "run_id": "r1", "status": "completed", "claims": [{"claim_id": "CL1"}],
        "evidence_anchors": [{"anchor_id": "A1"}],
        "admitted_concerns": [{
            "concern_id": "M1", "severity": "major", "title": "Test concern",
            "claim_ids": ["CL1"], "evidence_anchor_ids": ["A1"],
            "closure_criterion": "A prespecified check passes", "confidence": "high"
        }],
        "rejected_concerns": [], "warnings": [], "critical_gates": {}, "provenance_report": {}
    }
    (run / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (run / "config.json").write_text("{}", encoding="utf-8")
    (artifacts / "review.md").write_text("# Review", encoding="utf-8")
    ReviewWorkspace(run).set_concern_status("M1", "resolved", note="checked")
    result = freeze_run(run)
    assert result["quality"]["invalid_claim_references"] == 0
    assert result["quality"]["human_concern_statuses"]["resolved"] == 1
    with zipfile.ZipFile(result["bundle"]) as zf:
        names = set(zf.namelist())
        assert "handoff_manifest.json" in names
        assert "artifacts/closure_matrix.csv" in names

from referee.finalization import verify_handoff


def test_verify_handoff_accepts_frozen_bundle(tmp_path):
    run = tmp_path / "r2"; artifacts = run / "artifacts"; artifacts.mkdir(parents=True)
    state = {"run_id":"r2","status":"completed","claims":[],"evidence_anchors":[],"admitted_concerns":[],"rejected_concerns":[],"warnings":[],"critical_gates":{},"provenance_report":{}}
    (run / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (artifacts / "review.md").write_text("# Review", encoding="utf-8")
    result = freeze_run(run)
    verified = verify_handoff(result["bundle"])
    assert verified["valid"] is True
    assert verified["checked_files"] >= 3
