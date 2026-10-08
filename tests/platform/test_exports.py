from referee.exports.html_report import render_html

def test_html_report_contains_concern():
    h=render_html({'admitted_concerns':[{'severity':'major','title':'Leakage','closure_criterion':'Fix split'}]})
    assert 'Leakage' in h and '<html>' in h
