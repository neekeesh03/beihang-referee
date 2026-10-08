import json
from pathlib import Path
from referee.evals.corpus import load_corpus
from referee.validation.release import classify_evaluator_independence
from referee.validation.adversarial import run_adversarial_integrity_suite

ROOT=Path(__file__).resolve().parents[2]

def test_severity_calibration_covers_all_three_classes_with_specific_gold():
    rows=load_corpus('severity',ROOT/'benchmark_corpus')
    assert {r['structured_gold']['severity'] for r in rows}=={'major','minor','observation'}
    for r in rows:
        g=r['structured_gold']
        assert len(g['gold_scientific_consequence'])>50
        assert len(g['gold_closure_criterion'])>40
        assert g['scientific_consequence'][0]==g['gold_scientific_consequence']

def test_adversarial_suite_separates_contract_from_deterministic_integrity():
    r=run_adversarial_integrity_suite(ROOT)
    assert r['contract_test_pass_rate']==1.0
    assert r['deterministic_integrity_pass_rate']==1.0
    assert r['model_backed_adversarial_pass_rate'] is None
    assert all(c['test_type'] in {'static_contract','deterministic_integrity'} for c in r['cases'])

def test_same_model_is_internal_validation_not_independent():
    r=classify_evaluator_independence('model-x','model-x','model-x','model-x','model-x')
    assert r['label']=='internal_validation'
    assert not r['external_independent_validation']

def test_cross_model_judge_qualifies_as_independent_validation():
    r=classify_evaluator_independence('model-x','model-x','model-y','model-x','model-y')
    assert r['label']=='independent_validation'
    assert r['external_independent_validation']
