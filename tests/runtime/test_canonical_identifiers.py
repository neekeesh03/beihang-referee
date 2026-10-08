import json
import pytest
from referee.models import ReviewState
from referee.validation.identifiers import append_evidence_anchors, remap_concern_references, assert_unique_ids

def state(): return ReviewState(run_id="r",query="q",manuscript_paths=["x"],mode="deep")

def test_same_local_anchor_id_from_two_reviewers_gets_distinct_runtime_ids():
    s=state();m1=append_evidence_anchors(s,[{"anchor_id":"A001","quote_or_fact":"one"}],source_stage="STAT",reviewer_id="R01");m2=append_evidence_anchors(s,[{"anchor_id":"A001","quote_or_fact":"two"}],source_stage="METHOD",reviewer_id="R02")
    assert m1["A001"] != m2["A001"]
    assert [a["source_local_id"] for a in s.evidence_anchors] == ["A001","A001"]

def test_concern_reference_is_remapped_in_own_stage_context():
    c=remap_concern_references({"evidence_anchor_ids":["A001"]},anchor_map={"A001":"A-STAT-R01-0001"})
    assert c["evidence_anchor_ids"] == ["A-STAT-R01-0001"]

def test_duplicate_canonical_insertion_is_a_hard_programming_error():
    with pytest.raises(ValueError): assert_unique_ids([{"anchor_id":"A-X-0001"},{"anchor_id":"A-X-0001"}],"anchor_id","anchor")

def test_canonical_ids_survive_serialization_roundtrip():
    s=state();append_evidence_anchors(s,[{"anchor_id":"A001","quote_or_fact":"one"}],source_stage="STAT",reviewer_id="R01")
    restored=ReviewState.from_dict(json.loads(json.dumps(s.to_dict())))
    assert restored.evidence_anchors[0]["anchor_id"] == s.evidence_anchors[0]["anchor_id"]
