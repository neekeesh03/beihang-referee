from referee.verification.provenance import provenance_score

def test_provenance_score_high():
    c={'concern_id':'M1','evidence_anchor_ids':['A1']}
    a={'A1':{'document_id':'D1','locator':'Methods','quote_or_fact':'x','confidence':'high'}}
    assert provenance_score(c,a)['grade']=='high'
