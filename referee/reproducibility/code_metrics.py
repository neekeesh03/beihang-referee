from pathlib import Path
import re
def code_metrics(files):
    rows=[]
    for p in map(Path,files):
        if p.suffix.lower()=='.ipynb':continue
        try:text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:continue
        rows.append({'path':str(p),'lines':len(text.splitlines()),'seed_mentions':len(re.findall(r'(?i)random[_ .-]?seed|seed\s*=',text)),'hardcoded_absolute_paths':len(re.findall(r'(?:[A-Za-z]:\\|/Users/|/home/)',text)),'network_calls':len(re.findall(r'(?i)requests\.|httpx\.|urlopen|curl ',text))})
    return {'files':rows,'file_count':len(rows),'lines':sum(x['lines'] for x in rows)}
