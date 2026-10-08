from pathlib import Path
import json
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from referee.benchmarks import run_major_comment_eval
from referee.evals import load_corpus, all_case_count

lock = run_major_comment_eval(root / "evals" / "cases" / "major_comment_cases.json")
issues=[]
for row in load_corpus('scientific',root/'benchmark_corpus'):
    # Clean/minor/security-control cases intentionally have no major gold concern.
    gold = row.get('gold_concern')
    if not row.get('manuscript') or (gold is not None and not isinstance(gold,dict)):
        issues.append(row.get('case_id'))
for row in load_corpus('domain',root/'benchmark_corpus'):
    if not row.get('manuscript') or not isinstance(row.get('gold'),dict):issues.append(row.get('case_id'))
for row in load_corpus('revision',root/'benchmark_corpus'):
    if not row.get('old_text') or not row.get('new_text') or not row.get('expected_resolution'):issues.append(row.get('pair_id'))
for row in load_corpus('rebuttal',root/'benchmark_corpus'):
    if not row.get('response_text') or not row.get('expected_traceability'):issues.append(row.get('case_id'))
for row in load_corpus('severity',root/'benchmark_corpus'):
    if not row.get('manuscript') or not isinstance(row.get('structured_gold'),dict) or row.get('expected_severity') not in {'major','minor','observation'}: issues.append(row.get('case_id'))
ready=all_case_count(root/'benchmark_corpus')
result={
    'total':lock['total'],'passed':lock['passed'],'cases':lock.get('cases', lock.get('rows', [])),
    'evidence_lock':{'total':lock['total'],'passed':lock['passed']},
    'benchmark_readiness':{'cases':ready,'valid_cases':ready-len(issues),'invalid_case_ids':issues[:50]},
    'end_to_end_runner':'scripts/run_benchmark_suite.py',
    'mutation_runner':'scripts/run_mutation_benchmark.py',
    'ablation_runner':'scripts/run_ablation_benchmark.py',
}
print(json.dumps(result, indent=2))
raise SystemExit(0 if lock['passed']==lock['total'] and not issues and ready==1057 else 1)
