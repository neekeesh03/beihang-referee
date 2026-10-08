import xml.etree.ElementTree as ET
from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_json,get_text
class PubMedProvider(ScholarlyProvider):
    name='pubmed'
    async def search(self,query:str,*,limit:int=10):
        s=await get_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',params={'db':'pubmed','term':query,'retmode':'json','retmax':limit});ids=s.get('esearchresult',{}).get('idlist',[])
        if not ids:return []
        text=await get_text('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',params={'db':'pubmed','id':','.join(ids),'retmode':'xml'});root=ET.fromstring(text);out=[]
        for art in root.findall('.//PubmedArticle'):
            title=''.join(art.findtext('.//ArticleTitle') or '');pmid=art.findtext('.//PMID');year=art.findtext('.//PubDate/Year');doi=None
            for eid in art.findall('.//ArticleId'):
                if eid.attrib.get('IdType')=='doi':doi=eid.text
            out.append(ScholarlyRecord(title=title,year=int(year) if year and year.isdigit() else None,doi=doi,url=f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/' if pmid else None,provider=self.name,identifiers={'PMID':pmid} if pmid else {}))
        return out
