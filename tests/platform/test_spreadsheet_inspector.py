from pathlib import Path
from referee.ingestion.spreadsheets import inspect_xlsx
ROOT=Path(__file__).resolve().parents[2]/'fixtures'/'manuscripts'
def test_xlsx_formulas_detected():
    r=inspect_xlsx(ROOT/'synthetic_data.xlsx'); assert r['sheets'][0]['formulas']>=90
