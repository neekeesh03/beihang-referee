import re
PATTERNS={'openai_key':re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),'aws_access_key':re.compile(r'\bAKIA[0-9A-Z]{16}\b'),'generic_secret':re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\b\s*[:=]\s*[\"']?([^\s\"']{8,})")}
def scan_secrets(text:str)->list[dict]:
    out=[]
    for name,p in PATTERNS.items():
        for m in p.finditer(text):out.append({'type':name,'start':m.start(),'end':m.end(),'preview':m.group(0)[:8]+'…'})
    return out
