from referee.scholarly.base import ScholarlyRecord
from referee.scholarly.dedupe import deduplicate_records

def test_deduplicate_by_doi():
    a=ScholarlyRecord(title='A',doi='10.1/x')
    b=ScholarlyRecord(title='Different title',doi='https://doi.org/10.1/X')
    assert len(deduplicate_records([a,b]))==1
