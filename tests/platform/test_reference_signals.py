from referee.ingestion.references import extract_reference_signals

def test_extract_reference_signals():
    r=extract_reference_signals('doi 10.1234/ABC.7 PMID: 12345678 arXiv: 2401.01234 2024')
    assert '10.1234/ABC.7' in r['dois']
    assert '12345678' in r['pmids']
    assert '2401.01234' in r['arxiv_ids']
