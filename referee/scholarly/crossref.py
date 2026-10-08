from .base import ScholarlyProvider,ScholarlyRecord
from .http import get_json
class CrossrefProvider(ScholarlyProvider):
    name='crossref'
    def __init__(self,mailto:str|None=None):self.mailto=mailto
    async def search(self,query:str,*,limit:int=10):
        params={'query.bibliographic':query,'rows':limit}
        if self.mailto:params['mailto']=self.mailto
        data=await get_json('https://api.crossref.org/works',params=params);out=[]
        for x in data.get('message',{}).get('items',[]):
            title=(x.get('title') or [''])[0];year=((x.get('published-print') or x.get('published-online') or {}).get('date-parts') or [[None]])[0][0]
            out.append(ScholarlyRecord(title=title,year=year,doi=x.get('DOI'),url=x.get('URL'),authors=[' '.join(filter(None,[a.get('given'),a.get('family')])) for a in x.get('author',[])],venue=(x.get('container-title') or [None])[0],provider=self.name,raw=x))
        return out
