import asyncio
from referee.scholarly.base import ScholarlyProvider, ScholarlyRecord
from referee.scholarly.federated import FederatedScholarSearch
class P(ScholarlyProvider):
    name='p'
    async def search(self,q,*,limit=10):return [ScholarlyRecord(title='causal inference study',doi='10.1/a',provider='p')]
def test_federated_search():
    r=asyncio.run(FederatedScholarSearch([P()]).search('causal inference'))
    assert len(r['records'])==1
