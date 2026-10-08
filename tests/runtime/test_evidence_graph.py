from referee.evidence import build_evidence_graph_dot

def test_evidence_graph_links_anchor_claim_concern():
    dot = build_evidence_graph_dot({
        "claims":[{"claim_id":"C1","text":"claim"}],
        "evidence_anchors":[{"anchor_id":"A1","locator":"Methods","supports":"C1"}],
        "admitted_concerns":[{"concern_id":"M1","title":"issue","claim_ids":["C1"],"evidence_anchor_ids":["A1"],"closure_criterion":"fix it"}]
    })
    assert '"A1" -> "C1"' in dot
    assert '"A1" -> "M1"' in dot
    assert '"M1" -> "M1_closure"' in dot
