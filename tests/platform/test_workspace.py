import pytest
from referee.lifecycle import ReviewWorkspace


def test_workspace_keeps_human_overlay_separate(tmp_path):
    ws = ReviewWorkspace(tmp_path / "run")
    ws.add_note("Check Table S4", author="editor")
    ws.set_concern_status("C-1", "resolved", note="Verified in revision")
    data = ws.load()
    assert data["notes"][0]["author"] == "editor"
    assert data["concerns"]["C-1"]["status"] == "resolved"
    with pytest.raises(ValueError):
        ws.set_concern_status("C-1", "invented")
