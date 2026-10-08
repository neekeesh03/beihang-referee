from referee.reviewers.router import route_reviewers

def test_router_adds_ml_reviewer():
    r=route_reviewers({'design':'machine learning prediction'},[])
    assert 'ml_ai' in r
    assert 'statistics_causal' in r

def test_router_adds_electrochemistry_for_mfc():
    r=route_reviewers({'field':'microbial fuel cell electrochemistry'},[])
    assert 'electrochemistry_fuel_cells' in r
