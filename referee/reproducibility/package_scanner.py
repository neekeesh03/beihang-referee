from pathlib import Path
from .environment import detect_environment_files
from .data_manifest import build_data_manifest
from .code_metrics import code_metrics
from ..ingestion.notebooks import inspect_notebook
def scan_reproducibility_package(paths:list[str])->dict:
    files=[]
    for raw in paths:
        p=Path(raw);files.extend([x for x in p.rglob('*') if x.is_file()] if p.is_dir() else [p])
    code=[p for p in files if p.suffix.lower() in {'.py','.r','.jl','.m','.ipynb'}];notebooks=[]
    for p in code:
        if p.suffix.lower()=='.ipynb':
            try:notebooks.append(inspect_notebook(p))
            except Exception as e:notebooks.append({'path':str(p),'error':str(e)})
    return {'environment':detect_environment_files(files),'data':build_data_manifest(files),'code':code_metrics(code),'notebooks':notebooks,'has_code':bool(code)}
