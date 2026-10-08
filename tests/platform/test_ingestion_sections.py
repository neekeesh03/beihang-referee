from referee.ingestion.sections import split_sections

def test_sections_detect_markdown_headings():
    s=split_sections('# Title\nX\n## Methods\nM\n## Results\nR')
    assert any(x['title']=='Methods' for x in s)
    assert any(x['title']=='Results' for x in s)
