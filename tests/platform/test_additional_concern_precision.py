import asyncio
from referee.evals.judge import ScientificDefectEvaluator
from referee.providers.scripted import ScriptedLLMProvider

VALID={"status":"valid_additional","evidence_resolves":True,"mechanism_valid":"yes","consequence_proportionate":"yes","major_severity_justified":"yes","duplicate_of_gold":False,"confidence":0.95}
INVALID={"status":"invalid_additional","evidence_resolves":False,"mechanism_valid":"no","consequence_proportionate":"no","major_severity_justified":"no","duplicate_of_gold":False,"confidence":0.94}

def test_unmatched_concern_is_independently_judged_not_auto_false():
    llm=ScriptedLLMProvider({"additional_concern_A":VALID,"additional_concern_B":VALID})
    ev=ScientificDefectEvaluator(llm=llm,judge_model_a='judge-a',judge_model_b='judge-b')
    out=asyncio.run(ev.evaluate_additional('manuscript text',{'concern_id':'MC-X','severity':'major'}))
    assert out['final']['status']=='valid_additional'
    assert len(llm.calls)==2
    assert all(c.model in {'judge-a','judge-b'} for c in llm.calls)

def test_disagreement_becomes_uncertain_not_false():
    llm=ScriptedLLMProvider({"additional_concern_A":VALID,"additional_concern_B":INVALID})
    ev=ScientificDefectEvaluator(llm=llm,judge_model_a='judge-a',judge_model_b='judge-b')
    out=asyncio.run(ev.evaluate_additional('manuscript text',{'concern_id':'MC-X','severity':'major'}))
    assert out['final']['status']=='uncertain_additional'
