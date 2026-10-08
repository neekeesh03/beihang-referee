def test_completed_fixture_records_distinct_contexts():
    # Structural unit test of the verification-record invariant; full engine coverage lives in test_engine.
    from referee.validation import validate_state_consistency
    state={
      'claims':[{'claim_id':'C001'}],
      'evidence_anchors':[{'anchor_id':'A001'}],
      'admitted_concerns':[{
        'concern_id':'MC001','title':'A real issue','severity':'major','claim_ids':['C001'],'evidence_anchor_ids':['A001'],
        'failure_mechanism':'A specified mechanism causes a scientific failure.','scientific_consequence':'The central interpretation becomes unreliable.',
        'minimum_resolution':'Correct the analysis or narrow the claim.','closure_criterion':'Report the corrected result and demonstrate consistency.',
        'reviewer_confidence':0.9,'steelman':'A favorable interpretation is possible but does not remove the failure.',
        'steelman_survives':True,'steelman_survival_reason':'The documented limitation remains under the favorable interpretation.',
        'external_verification_required':False,'uncertainties':[],'suggested_validation_checks':[],
        'provenance_gate':{'status':'passed'}}],
      'verification_records':[{'concern_id':'MC001','verification_status':'verified','generator_context_id':'ctx-a','verifier_context_id':'ctx-b'}],
      'critical_gates':{},'final_review':{}}
    assert validate_state_consistency(state)==[]
