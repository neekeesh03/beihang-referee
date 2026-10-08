from referee.documents import DocumentLoader

def test_text_loader(tmp_path):
    p = tmp_path / "paper.md"
    p.write_text("# Test\nA result.", encoding="utf-8")
    d = DocumentLoader().load(p)
    assert "A result" in d.text
    assert d.metadata["characters"] > 0
