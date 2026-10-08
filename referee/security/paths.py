from pathlib import Path
def safe_output_path(root,path):
    r=Path(root).resolve();p=(r/path).resolve()
    if r!=p and r not in p.parents:raise ValueError('output path escapes run root')
    return p
