from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_json
class OpenAlexProvider(ScholarlyProvider):
    name='openalex'
    def __init__(self,mailto:str|None=None):self.mailto=mailto
    async def search(self,query:str,*,limit:int=10):
        params={'search':query,'per-page':limit}
        if self.mailto:params['mailto']=self.mailto
        data=await get_json('https://api.openalex.org/works',params=params);out=[]
        for x in data.get('results',[]):
            ids=x.get('ids') or {};doi=(ids.get('doi') or '').replace('https://doi.org/','') or None
            src=(x.get('primary_location') or {}).get('source') or {}
            out.append(ScholarlyRecord(title=x.get('title') or '',year=x.get('publication_year'),doi=doi,url=x.get('doi') or x.get('id'),authors=[a.get('author',{}).get('display_name','') for a in x.get('authorships',[])],venue=src.get('display_name'),provider=self.name,citation_count=x.get('cited_by_count'),raw=x))
        return out
