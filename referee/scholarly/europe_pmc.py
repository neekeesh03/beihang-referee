from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_json
class EuropePMCProvider(ScholarlyProvider):
    name='europe_pmc'
    async def search(self,query:str,*,limit:int=10):
        data=await get_json('https://www.ebi.ac.uk/europepmc/webservices/rest/search',params={'query':query,'format':'json','pageSize':limit});out=[]
        for x in data.get('resultList',{}).get('result',[]):
            year=int(x['pubYear']) if str(x.get('pubYear','')).isdigit() else None
            out.append(ScholarlyRecord(title=x.get('title') or '',year=year,doi=x.get('doi'),url=('https://europepmc.org/article/MED/'+x['pmid']) if x.get('pmid') else None,authors=[a.strip() for a in (x.get('authorString') or '').split(',') if a.strip()],venue=x.get('journalTitle'),provider=self.name,citation_count=int(x['citedByCount']) if str(x.get('citedByCount','')).isdigit() else None,identifiers={k.upper():str(x[k]) for k in ('pmid','pmcid') if x.get(k)},raw=x))
        return out
