from pathlib import Path
from referee.ingestion.docx_inspector import inspect_docx
ROOT=Path(__file__).resolve().parents[2]/'fixtures'/'binary_regression'
def test_tracked_changes_fixture():
    r=inspect_docx(ROOT/'structural_00.docx')
    assert r['tracked_insertions']>=1 and r['tracked_deletions']>=1
def test_comments_fixture():
    r=inspect_docx(ROOT/'structural_00.docx')
    assert r['comments_present'] is True
