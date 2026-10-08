from referee.reviewers.consensus import consensus_summary

def test_consensus_clusters_same_concern():
    s={'t1':{'specialist':'a','result':{'concerns':[{'title':'Leakage','claim_ids':['C1']}]}},'t2':{'specialist':'b','result':{'concerns':[{'title':'Leakage','claim_ids':['C1']}]}}}
    out=consensus_summary(s)
    assert out['clusters'][0]['reviewer_count']==2
