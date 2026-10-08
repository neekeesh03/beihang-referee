def assess_closure_test(criterion:str)->dict:
    c=(criterion or '').strip();observable=any(w in c.lower() for w in ['demonstrate','report','remove','provide','show','recalculate','validate','replicate','reframe','include','match'])
    return {'criterion':c,'nonempty':bool(c),'actionable':len(c)>=20 and observable,'status':'testable' if len(c)>=20 and observable else 'weak'}
