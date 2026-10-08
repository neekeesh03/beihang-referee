import hashlib
from referee.stages.core import _materialize_literature_anchors
from referee.verification import verify_anchor_integrity


def test_external_anchor_hash_and_status_are_recomputed_from_opened_content():
    content='The prior study reports a 12 percent improvement over baseline.'
    ledger=[{'query':'q','results':[{'url':'https://example.test/paper','doi':'10.1/x','title':'Prior study','provider':'test','raw_content':content,'content_status':'provided_by_retriever'}]}]
    model_anchor={
      'anchor_id':'A900','source_type':'external','document_id':'10.1/x','locator':'abstract',
      'quote_or_fact':'reports a 12 percent improvement','supports':'C001','confidence':'high',
      'url':'https://example.test/paper','content_status':'fetched','content_sha256':'fabricated'}
    [a]=_materialize_literature_anchors([model_anchor],ledger)
    assert a['_model_content_sha256_ignored']=='fabricated'
    assert a['content_sha256']==hashlib.sha256(content.encode()).hexdigest()
    report=verify_anchor_integrity([a],[])
    assert report['anchors'][0]['status']=='external_verified'
    assert report['anchors'][0]['supplied_content_sha256_ignored']==a['content_sha256']


def test_external_anchor_without_opened_matching_content_fails_closed():
    anchor={'anchor_id':'A901','source_type':'external','document_id':'x','locator':'abstract','quote_or_fact':'a fact','supports':'C001','confidence':'high','content_status':'fetched','content_sha256':'pretend'}
    [a]=_materialize_literature_anchors([anchor],[{'query':'q','results':[]}])
    report=verify_anchor_integrity([a],[])
    assert report['anchors'][0]['status']=='invalid'
