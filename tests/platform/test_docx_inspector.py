from pathlib import Path
from referee.ingestion.docx_inspector import inspect_docx
ROOT=Path(__file__).resolve().parents[2]/'fixtures'/'manuscripts'
def test_omml_detected():
    r=inspect_docx(ROOT/'fixture_omml_0.docx'); assert r['omml_equations']>=1
def test_plaintext_math_detected():
    r=inspect_docx(ROOT/'fixture_plaintext_math_0.docx'); assert r['possible_plaintext_math']>=1
