from pathlib import Path
from referee.evals import all_case_count, evaluate_counterfactual_pair, ABLATIONS
from referee.evals.scoring import aggregate

def test_all_validation_cases_are_addressable_by_eval_platform():
    assert all_case_count(Path(__file__).resolve().parents[2]/'benchmark_corpus')==1057

def test_counterfactual_requires_concern_to_disappear():
    gold={'title':'Data leakage','failure_mechanism':'Feature selection uses held-out folds'}
    bad=[{'concern_id':'M1','title':'Data leakage before cross-validation','failure_mechanism':'Held-out folds influence feature selection'}]
    fixed=[]
    r=evaluate_counterfactual_pair(gold,'data_leakage',bad,fixed)
    assert r['causal_sensitivity_pass']

def test_ablation_matrix_contains_full_system_and_verifier_ablation():
    names={x.name for x in ABLATIONS};assert 'full_system' in names and 'no_independent_verifier' in names
