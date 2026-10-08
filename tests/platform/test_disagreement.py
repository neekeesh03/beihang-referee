from referee.reviewers.disagreement import disagreement_map

def test_disagreement_detected():
    s={'t1':{'specialist':'a','result':{'concerns':[{'title':'A'}]}},'t2':{'specialist':'b','result':{'concerns':[{'title':'B'}]}}}
    assert disagreement_map(s)['requires_adjudication'] is True
