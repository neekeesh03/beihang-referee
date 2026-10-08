from referee.verification.citations import CitationVerifier, decisive_external_evidence_ok

V=CitationVerifier()
SRC={"doi":"10.1234/real","title":"Real Study","provider":"crossref"}

def check(prop,content):
    return V.verify({"citation_id":"x","source_identifier":"10.1234/real","title":"Real Study"},{**SRC,"raw_content":content},proposition=prop)

def test_negation_outperformed_is_contradicted():
    r=check("Method A outperformed B.","Method A did not outperform B.")
    assert r["proposition_support"]=="contradicted"
    assert not decisive_external_evidence_ok(r)

def test_negation_mortality_is_contradicted():
    assert check("Exposure increased mortality.","No increase in mortality was observed.")["proposition_support"]=="contradicted"

def test_negation_association_is_contradicted():
    assert check("Treatment was associated with improved survival.","Treatment was not associated with improved survival.")["proposition_support"]=="contradicted"

def test_causal_scope_denial_cannot_be_supported_by_overlap():
    r=check("X caused Y.","The study cannot establish whether X caused Y.")
    assert r["proposition_support"]!="supported"

def test_paraphrase_overlap_alone_is_never_supported():
    r=check("Method A improved survival after treatment.","The study discusses method A, survival, and treatment but provides no result establishing improvement.")
    assert r["proposition_support"]!="supported"

def test_independent_entailment_can_support_paraphrase():
    r=V.verify({"citation_id":"x","source_identifier":"10.1234/real","title":"Real Study"},{**SRC,"raw_content":"Participants receiving A had longer survival than controls."},proposition="Treatment A improved survival.",entailment={"status":"supported","supporting_passage":"Participants receiving A had longer survival than controls.","contradicting_passage":"","confidence":0.96})
    assert r["proposition_support"]=="supported"
    assert r["entailment_method"]=="independent-entailment"
