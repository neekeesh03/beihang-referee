from referee.stages import stages_for_mode

def ids(mode): return [s.stage_id for s in stages_for_mode(mode)]
def test_modes_are_real_distinct_dags():
    assert ids('initial') != ids('revision')
    assert '01c_revision_preparation' in ids('revision') and '13a_revision_closure' in ids('revision')
    assert '01c_rebuttal_preparation' in ids('rebuttal') and '13a_rebuttal_closure' in ids('rebuttal')
    assert ids('meta_review') == ['01_intake','02_policy_security','20_meta_review']
    assert '08_specialists' not in ids('editorial_screen')
    assert ids('reproducibility')[-1]=='20_reproducibility_synthesis'
