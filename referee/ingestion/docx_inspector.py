from __future__ import annotations
from pathlib import Path
import zipfile, xml.etree.ElementTree as ET, re
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'; M='http://schemas.openxmlformats.org/officeDocument/2006/math'
def _count(root, uri, local): return sum(1 for x in root.iter() if x.tag==f'{{{uri}}}{local}')
def inspect_docx(path:str|Path)->dict:
    p=Path(path); out={'path':str(p),'kind':'docx','bytes':p.stat().st_size}
    with zipfile.ZipFile(p) as z:
        names=set(z.namelist()); root=ET.fromstring(z.read('word/document.xml'))
        text=' '.join((x.text or '') for x in root.iter() if x.tag==f'{{{W}}}t')
        out.update({'paragraphs':_count(root,W,'p'),'tables':_count(root,W,'tbl'),'omml_equations':_count(root,M,'oMath')+_count(root,M,'oMathPara'),'tracked_insertions':_count(root,W,'ins'),'tracked_deletions':_count(root,W,'del'),'comments_present':'word/comments.xml' in names,'footnotes_present':'word/footnotes.xml' in names,'endnotes_present':'word/endnotes.xml' in names,'embedded_media':len([n for n in names if n.startswith('word/media/') and not n.endswith('/')]),'embedded_objects':len([n for n in names if n.startswith('word/embeddings/') and not n.endswith('/')]),'external_links':0,'text_characters':len(text),'possible_plaintext_math':len(re.findall(r'\b(?:R|r)\^2\b|[A-Za-z]_\{?\w+|\\frac\b',text))})
        rel='word/_rels/document.xml.rels'
        if rel in names:
            rr=ET.fromstring(z.read(rel)); out['external_links']=sum(1 for e in rr if e.attrib.get('TargetMode')=='External')
    return out
