from referee.validation import validate_major_comment

def test_major_comment_rejects_missing_closure():
    c = {
        "concern_id":"M1", "title":"x", "severity":"major", "claim_ids":["C1"],
        "evidence_anchor_ids":["A1"], "failure_mechanism":"f", "scientific_consequence":"s",
        "minimum_resolution":"m", "closure_criterion":"", "confidence":"high",
        "source_agent":"methods", "steelman_survives":True,
    }
    errors = validate_major_comment(c, {"A1"})
    assert any("closure_criterion" in e for e in errors)

def test_major_comment_rejects_unknown_anchor():
    c = {
        "concern_id":"M1", "title":"x", "severity":"major", "claim_ids":["C1"],
        "evidence_anchor_ids":["A404"], "failure_mechanism":"f", "scientific_consequence":"s",
        "minimum_resolution":"m", "closure_criterion":"c", "confidence":"high",
        "source_agent":"methods", "steelman_survives":True,
    }
    assert any("unknown anchors" in e for e in validate_major_comment(c, {"A1"}))
