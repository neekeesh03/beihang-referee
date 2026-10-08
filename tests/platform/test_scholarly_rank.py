from referee.scholarly.base import ScholarlyRecord
from referee.scholarly.ranking import rank_records

def test_rank_title_overlap():
    rows=[ScholarlyRecord(title='Unrelated chemistry'),ScholarlyRecord(title='causal inference cohort study')]
    assert rank_records(rows,'causal inference')[0].title.startswith('causal')
