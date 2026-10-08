from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_json
class SemanticScholarProvider(ScholarlyProvider):
    name='semantic_scholar'
    def __init__(self,api_key:str|None=None):self.api_key=api_key
    async def search(self,query:str,*,limit:int=10):
        headers={'x-api-key':self.api_key} if self.api_key else None;fields='title,year,authors,abstract,venue,url,externalIds,citationCount'
        data=await get_json('https://api.semanticscholar.org/graph/v1/paper/search',params={'query':query,'limit':limit,'fields':fields},headers=headers);out=[]
        for x in data.get('data',[]):
            ids=x.get('externalIds') or {};out.append(ScholarlyRecord(title=x.get('title') or '',year=x.get('year'),doi=ids.get('DOI'),url=x.get('url'),authors=[a.get('name','') for a in x.get('authors',[])],abstract=x.get('abstract'),venue=x.get('venue'),provider=self.name,citation_count=x.get('citationCount'),identifiers={k:str(v) for k,v in ids.items() if v},raw=x))
        return out
