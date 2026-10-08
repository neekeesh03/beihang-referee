from referee.evals.judge import deterministic_judge_a, deterministic_judge_b, deterministic_adjudicate

def gold():
    return {
      "defect_id":"DATA_LEAKAGE_PRE_CV_FEATURE_SELECTION","category":"data_leakage","severity":"major",
      "required_mechanism_concepts":[
        {"concept":"feature selection occurs before fold separation","acceptable_phrases":["feature selection before cross validation","variable screening uses all observations before folds are formed"]},
        {"concept":"held-out observations influence model construction","acceptable_phrases":["held-out observations influence feature selection","test-fold information affects predictors entering each training model"]},
      ],
      "scientific_consequence":["estimated held-out performance may be optimistically biased"],
      "acceptable_resolutions":["perform feature selection independently inside every training fold"],
      "forbidden_misdiagnoses":["insufficient sample size","lack of external validation alone"],
    }

def judge(c):
    a=deterministic_judge_a(gold(),c);b=deterministic_judge_b(gold(),c);return deterministic_adjudicate(gold(),c,a,b)

def base(mech,consequence="estimated held-out performance may be optimistically biased",severity="major"):
    return {"title":"Concern","failure_mechanism":mech,"scientific_consequence":consequence,"minimum_resolution":"perform feature selection independently inside every training fold","closure_criterion":"selection is nested inside every fold","severity":severity}

def test_generic_language_does_not_count_as_detection():
    assert judge(base("The validation strategy and feature selection procedure should be described more clearly."))["mechanism_match"] != "yes"

def test_correct_category_wrong_mechanism_does_not_count():
    assert judge(base("The model may overfit because the sample size is small."))["mechanism_match"] != "yes"

def test_correct_mechanism_with_different_wording_counts():
    out=judge(base("Variable screening uses all observations before folds are formed, so test-fold information affects predictors entering each training model."))
    assert out["mechanism_match"] == "yes"

def test_correct_mechanism_exaggerated_consequence_is_scored_separately():
    out=judge(base("Variable screening uses all observations before folds are formed, so test-fold information affects predictors entering each training model.","Therefore every result in the manuscript is invalid."))
    assert out["mechanism_match"] == "yes"
    assert out["consequence_match"] != "yes"
