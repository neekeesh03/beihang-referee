from pathlib import Path
from referee.ingestion.latex_inspector import inspect_latex
ROOT=Path(__file__).resolve().parents[2]/'fixtures'/'manuscripts'
def test_unresolved_latex_ref():
    r=inspect_latex(ROOT/'synthetic_paper.tex'); assert 'fig:missing' in r['unresolved_refs']
