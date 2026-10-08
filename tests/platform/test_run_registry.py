from referee.lifecycle import RunRegistry


def test_run_registry_round_trip(tmp_path):
    reg = RunRegistry(tmp_path / "runs")
    reg.upsert("r1", status="running", review_mode="initial", depth_mode="deep", query="q", input_count=2)
    reg.upsert("r1", status="completed", review_mode="initial", depth_mode="deep", query="q", input_count=2, summary={"admitted_major_comments": 3})
    row = reg.get("r1")
    assert row["status"] == "completed"
    assert row["summary"]["admitted_major_comments"] == 3
    assert reg.list()[0]["run_id"] == "r1"
