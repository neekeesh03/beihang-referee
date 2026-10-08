from referee.verification import CitationVerifier

V=CitationVerifier()
SRC={"doi":"10.1234/real","title":"Real Study","year":2024,"authors":["A Author"],"venue":"Journal X","provider":"crossref","raw_content":"Method A consistently outperformed B in the held-out cohort."}

def test_fake_doi_is_not_found():
    assert V.verify({"citation_id":"x","source_identifier":"10.9999/fake"},None,proposition="x")["existence_status"] == "not_found"

def test_real_doi_fake_title_is_metadata_mismatch():
    r=V.verify({"citation_id":"x","source_identifier":"10.1234/real","title":"Fake Study"},SRC,proposition="Method A consistently outperformed B")
    assert r["existence_status"] == "verified" and r["metadata_status"] == "mismatch"

def test_real_citation_fabricated_finding_is_not_supported():
    assert V.verify({"citation_id":"x","source_identifier":"10.1234/real","title":"Real Study"},SRC,proposition="Method C cured disease")["proposition_support"] in {"uncertain","not_supported","contradicted"}

def test_correct_citation_and_finding_are_supported():
    r=V.verify({"citation_id":"x","source_identifier":"10.1234/real","title":"Real Study","year":2024},SRC,proposition="Method A consistently outperformed B")
    assert r["existence_status"] == "verified" and r["metadata_status"] in {"match","partial_match"} and r["proposition_support"] == "supported"

def test_title_only_source_is_not_silently_existence_verified():
    r=V.verify({"citation_id":"x","title":"Real Study"},{"title":"Real Study","provider":"crossref","raw_content":"text"},proposition="text")
    assert r["existence_status"] in {"ambiguous","unverifiable"}
