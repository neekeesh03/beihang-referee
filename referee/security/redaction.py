from .secrets import scan_secrets
def redact_secrets(text:str)->str:
    spans=scan_secrets(text);out=text
    for s in sorted(spans,key=lambda x:x['start'],reverse=True):out=out[:s['start']]+'[REDACTED_SECRET]'+out[s['end']:]
    return out
