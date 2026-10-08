from pathlib import Path
from referee.ingestion.notebooks import inspect_notebook
ROOT=Path(__file__).resolve().parents[2]/'fixtures'/'manuscripts'
def test_notebook_inspector():
    r=inspect_notebook(ROOT/'synthetic_analysis.ipynb'); assert r['code_cells']==1 and r['execution_monotonic']
