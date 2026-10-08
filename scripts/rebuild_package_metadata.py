from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import date

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / 'scripts' / 'sync_runtime_assets.py')], check=True)
subprocess.run([sys.executable, str(root / 'scripts' / 'build_single_prompt.py')], check=True)
exclude = {'MANIFEST.json', 'checksums.sha256'}
ignored_parts = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.git', 'build', '.venv', 'venv', 'release-dist', 'wheelhouse'}
files = []
for p in sorted(x for x in root.rglob('*') if x.is_file()):
    rel_path = p.relative_to(root)
    rel = rel_path.as_posix()
    if rel in exclude or rel.endswith('.pyc') or any(part in ignored_parts or part.endswith('.egg-info') for part in rel_path.parts):
        continue
    files.append({'path': rel, 'size': p.stat().st_size})

def count_jsonl(path):
    return sum(1 for _ in path.open('r', encoding='utf-8')) if path.exists() else 0

manifest = {
    'name': 'Beihang Referee',
    'build_date': date.today().isoformat(),
    'description': 'Evidence-grounded agentic peer review for scientific manuscripts',
    'skills': len(list((root / 'skills').glob('*/SKILL.md'))),
    'agents': len(list((root / 'agents').glob('*.md'))),
    'runtime_modules': len(list((root / 'referee').rglob('*.py'))),
    'tests': len(list((root / 'tests').rglob('test_*.py'))),
    'guideline_profiles': len(list((root / 'profiles' / 'guidelines').glob('*.json'))),
    'domain_pack_profiles': len(list((root / 'profiles' / 'domain_packs').glob('*.json'))),
    'configuration_profiles': len(list((root / 'config' / 'profiles').glob('*.json'))),
    'binary_docx_fixtures': len(list((root / 'fixtures').rglob('*.docx'))),
    'benchmark_cases': {
        'scientific_defect_cases': count_jsonl(root / 'benchmark_corpus' / 'scientific_defect_cases.jsonl'),
        'revision_pairs': count_jsonl(root / 'benchmark_corpus' / 'revision_pairs.jsonl'),
        'rebuttal_cases': count_jsonl(root / 'benchmark_corpus' / 'rebuttal_cases.jsonl'),
        'domain_science_cases': count_jsonl(root / 'benchmark_corpus' / 'domain_science_cases.jsonl'),
        'severity_calibration_cases': count_jsonl(root / 'benchmark_corpus' / 'severity_calibration_cases.jsonl'),
    },
    'files': files,
}
(root / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
lines=[]
for item in files:
    p=root/item['path'];lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {item['path']}")
(root/'checksums.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Rebuilt manifest and checksums:', len(files), 'files')
