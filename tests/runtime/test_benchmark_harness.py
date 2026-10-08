from pathlib import Path
from referee.benchmarks import run_major_comment_eval

def test_major_comment_eval_all_cases_pass():
    r = run_major_comment_eval(str(Path(__file__).resolve().parents[2] / 'evals/cases/major_comment_cases.json'))
    assert r['passed'] == r['total']
