import ast
from pathlib import Path

def test_every_stage_llm_call_declares_schema():
    root=Path(__file__).resolve().parents[2]/'referee'/'stages'
    missing=[]
    for p in root.glob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n,ast.Await) and isinstance(n.value,ast.Call):
                f=n.value.func
                name=f.id if isinstance(f,ast.Name) else getattr(f,'attr','')
                if name=='_call' and not any(k.arg=='schema' for k in n.value.keywords):missing.append(f'{p.name}:{n.lineno}')
    assert not missing, missing
