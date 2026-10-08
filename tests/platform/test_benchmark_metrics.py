from referee.evals.scoring import aggregate


def test_benchmark_metrics_include_requested_scientific_dimensions():
    rows=[
        {"has_gold_defect":True,"detected":True,"gold_severity":"major","pred_severity":"major","predicted_major_count":1,"false_major_count":0,"ccore_case_false_positive":False,"anchor_validity":1.0,"claim_id_validity":1.0,"evidence_entailment_pass_rate":1.0,"mechanism_correctness":.8,"consequence_correctness":.7,"closure_quality":.9,"hallucinated_citation_rate":0.0,"llm_calls":4,"search_calls":1,"latency_seconds":2.0},
        {"has_gold_defect":False,"detected":False,"gold_severity":"none","pred_severity":"none","predicted_major_count":0,"false_major_count":0,"ccore_case_false_positive":False,"anchor_validity":None,"claim_id_validity":None,"evidence_entailment_pass_rate":None,"mechanism_correctness":None,"consequence_correctness":None,"closure_quality":None,"hallucinated_citation_rate":0.0,"llm_calls":3,"search_calls":0,"latency_seconds":1.0},
    ]
    m=aggregate(rows)
    assert m["defect_recall"]==1.0
    assert m["major_concern_precision"]==1.0
    assert m["ccore_case_false_positive_rate"]==0.0
    assert m["mean_mechanism_correctness"]==0.8
    assert m["mean_consequence_correctness"]==0.7
    assert m["mean_closure_quality"]==0.9
    assert m["mean_evidence_entailment_pass_rate"]==1.0
