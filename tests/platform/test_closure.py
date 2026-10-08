from referee.verification.closure import assess_closure_test

def test_closure_actionable():
    assert assess_closure_test('Report the corrected denominator and demonstrate that all tables match.')['actionable']
