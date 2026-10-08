from referee.reporting.checklist import heuristic_checklist

def test_reporting_is_not_formal_compliance():
    p={'name':'X','signal_checks':[{'id':'a','label':'Registration','terms':['registration']} ]}
    r=heuristic_checklist('trial registration is reported',p)
    assert r['formal_compliance_assessed'] is False
    assert r['items'][0]['status']=='signal_present'
