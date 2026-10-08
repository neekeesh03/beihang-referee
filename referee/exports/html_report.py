import html,json
def render_html(state:dict)->str:
    fr=state.get('final_review') or {};majors=fr.get('major_comments') or state.get('admitted_concerns') or []
    rows=''.join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"%(html.escape(str(c.get('severity',''))),html.escape(str(c.get('title',''))),html.escape(str(c.get('closure_criterion','')))) for c in majors)
    brief=html.escape(json.dumps(fr.get('decision_brief',{}),ensure_ascii=False,indent=2))
    return '<!doctype html><html><head><meta charset="utf-8"><title>Peer Review</title><style>body{font-family:system-ui;max-width:1100px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px;vertical-align:top}pre{white-space:pre-wrap}</style></head><body><h1>Peer Review Report</h1><h2>Decision brief</h2><pre>'+brief+'</pre><h2>Verified major concerns</h2><table><tr><th>Severity</th><th>Concern</th><th>Closure criterion</th></tr>'+rows+'</table></body></html>'
