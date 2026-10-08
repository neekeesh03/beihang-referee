from __future__ import annotations
from pathlib import Path
def inspect_xlsx(path:str|Path)->dict:
    try: import openpyxl
    except ImportError as exc: raise RuntimeError('XLSX inspection requires openpyxl') from exc
    p=Path(path); wb=openpyxl.load_workbook(p,read_only=False,data_only=False); sheets=[]
    for ws in wb.worksheets:
        formulas=errors=0
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value,str) and c.value.startswith('='): formulas+=1
                if isinstance(c.value,str) and c.value.startswith('#'): errors+=1
        sheets.append({'name':ws.title,'max_row':ws.max_row,'max_column':ws.max_column,'formulas':formulas,'error_like_cells':errors,'merged_ranges':len(ws.merged_cells.ranges)})
    return {'path':str(p),'sheets':sheets,'sheet_count':len(sheets),'defined_names':len(wb.defined_names)}
