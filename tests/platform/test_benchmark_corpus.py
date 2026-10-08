import json
from pathlib import Path

def test_corpus_is_synthetic_and_large():
    p=Path(__file__).resolve().parents[2]/'benchmark_corpus'/'scientific_defect_cases.jsonl'
    rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
    assert len(rows)>=400
    assert all(r['synthetic'] for r in rows[:20])
