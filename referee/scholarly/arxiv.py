import xml.etree.ElementTree as ET
from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_text
class ArxivProvider(ScholarlyProvider):
    name='arxiv'
    async def search(self,query:str,*,limit:int=10):
        text=await get_text('https://export.arxiv.org/api/query',params={'search_query':f'all:{query}','start':0,'max_results':limit});root=ET.fromstring(text);ns={'a':'http://www.w3.org/2005/Atom'};out=[]
        for e in root.findall('a:entry',ns):
            url=e.findtext('a:id',default='',namespaces=ns);published=e.findtext('a:published',default='',namespaces=ns);year=int(published[:4]) if published[:4].isdigit() else None
            out.append(ScholarlyRecord(title=' '.join((e.findtext('a:title',default='',namespaces=ns)).split()),year=year,url=url,authors=[a.findtext('a:name',default='',namespaces=ns) for a in e.findall('a:author',ns)],abstract=' '.join((e.findtext('a:summary',default='',namespaces=ns)).split()),provider=self.name))
        return out
