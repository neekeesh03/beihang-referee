import re,unicodedata
def normalize_title(s:str)->str:
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9]+',' ',s).strip()
def normalize_doi(s:str|None)->str|None:
    if not s:return None
    s=s.strip().lower();s=re.sub(r'^https?://(?:dx\.)?doi\.org/','',s);return s.rstrip(' .;,')
