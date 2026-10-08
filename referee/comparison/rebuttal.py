import re
def audit_rebuttal_structure(text:str)->dict:
    numbered=len(re.findall(r'(?m)^\s*(?:reviewer|comment|response|point)\s*\d+',text,re.I));cites=len(re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+',text,re.I));page_refs=len(re.findall(r'(?i)page\s+\d+|line[s]?\s+\d+',text))
    return {'structured_response_markers':numbered,'doi_mentions':cites,'page_or_line_references':page_refs,'traceability':'strong' if numbered and page_refs else 'partial' if numbered else 'weak'}
