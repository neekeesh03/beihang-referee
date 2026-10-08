from .base import ScholarlyProvider, ScholarlyRecord
from .registry import ScholarlyRegistry
from .dedupe import deduplicate_records
from .ranking import rank_records
__all__=["ScholarlyProvider","ScholarlyRecord","ScholarlyRegistry","deduplicate_records","rank_records"]
