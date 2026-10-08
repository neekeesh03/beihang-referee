import re
def compact_text(text,max_chars=12000):
    text=re.sub(r'\n{3,}','\n\n',text or '').strip();return text if len(text)<=max_chars else text[:max_chars]+'\n[truncated]'
