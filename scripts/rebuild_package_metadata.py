from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import date

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / 'scripts' / 'sync_runtime_assets.py')], check=True)
subprocess.run([sys.executable, str(root / 'scripts' / 'build_single_prompt.py')], check=True)
# Build the release file list from version-controlled sources rather than a
# recursive directory scan. A scan can accidentally ship ignored private data,
# such as .env, review manuscripts, credentials or local run artifacts.
exclude = {'MANIFEST.json', 'checksums.sha256'}
forbidden_parts = {'.git', '.venv', 'venv', 'env', 'runs', 'artifacts', '.referee',
                   'release-dist', 'wheelhouse', 'build', '__pycache__',
                   '.pytest_cache', '.mypy_cache', '.ruff_cache'}
forbidden_suffixes = ('.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.pyc')

if (root / '.git').exists():
    # Use tracked/staged files only. New source files must be `git add`ed
    # before creating release metadata; .gitignore is respected by Git.
    listed = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'],
                            check=True, capture_output=True).stdout
    candidates = [Path(x.decode('utf-8')) for x in listed.split(b'\0') if x]
else:
    # GitHub's downloadable source ZIP contains no .git. Its previously
    # frozen manifest is the allowlist, so added local files cannot leak.
    frozen_manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
    candidates = [Path(item['path']) for item in frozen_manifest['files']]

files = []
for rel_path in sorted(set(candidates), key=lambda p: p.as_posix()):
    rel = rel_path.as_posix()
    if rel in exclude:
        continue
    if rel_path.is_absolute() or '..' in rel_path.parts:
        raise RuntimeError(f'Unsafe release path: {rel}')
    if (any(part in forbidden_parts or part.endswith('.egg-info') for part in rel_path.parts)
            or (rel_path.name.startswith('.env') and rel_path.name != '.env.example')
            or rel_path.name.endswith(forbidden_suffixes)
            or rel_path.name == '.DS_Store'):
        raise RuntimeError(f'Private or generated file tracked in release sources: {rel}')
    p = root / rel_path
    if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root):
        raise RuntimeError(f'Missing, symlinked, or unsafe release source: {rel}')
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
