from referee.comparison import audit_rebuttal_structure

def test_rebuttal_traceability():
    r=audit_rebuttal_structure('Reviewer 1 Comment 1\nResponse 1: changed page 4, lines 20-30.')
    assert r['traceability']=='strong'
