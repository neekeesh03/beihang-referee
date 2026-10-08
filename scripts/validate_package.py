from pathlib import Path
import hashlib
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
required=[
 'README.md','QUICKSTART.md','pyproject.toml','CONTRIBUTING.md','SUPPORT.md','SECURITY.md','CODE_OF_CONDUCT.md','LICENSE','.gitignore',
 'core/PEER_REVIEW_PROMPT.md','core/INDEPENDENT_VERIFIER_PROMPT.md','core/BENCHMARK_JUDGE_PROMPT.md','core/BENCHMARK_ADJUDICATOR_PROMPT.md','core/AGENT_SYSTEM.md','core/POLICY_GATE.md','core/CLAIM_BURDEN_MATRIX.md','core/LITERATURE_SEARCH_PROTOCOL.md','core/REVIEW_RELIABILITY_PROTOCOL.md',
 'workflow/PIPELINE.md','guidelines/PUBLISHER_POLICY_REGISTRY.md','config/defaults.json','config/benchmark_profiles/TEMPLATE.json','config/benchmark_profiles/nature-published.json','config/journal_profiles/TEMPLATE.json','schemas/evidence_anchor.schema.json','schemas/major_comment.schema.json','schemas/core_peer_review.schema.json','schemas/independent_verifier.schema.json','schemas/real_world_benchmark.schema.json',
 'referee/engine.py','referee/stages/core.py','referee/stages/platform.py','referee/stages/modes.py','referee/contracts/concern.py','referee/contracts/schemas.py','referee/ingestion/docx_inspector.py',
 'referee/scholarly/federated.py','referee/providers/scholarly_search.py','referee/comparison/revision_diff.py','referee/server/app.py',
 'referee/lifecycle/registry.py','referee/lifecycle/workspace.py','referee/finalization/bundle.py','referee/profiles/registry.py','referee/_resources.py','referee/_assets/core/AGENT_SYSTEM.md',
 'examples/demo_manuscript.md','examples/demo_responses.json','examples/expected_demo_review.md','docs/README.md','scripts/build_release.py',
 'benchmark_corpus/scientific_defect_cases.jsonl','benchmark_corpus/severity_calibration_cases.jsonl','benchmark_corpus/revision_pairs.jsonl','benchmark_corpus/rebuttal_cases.jsonl','benchmark_corpus/domain_science_cases.jsonl','benchmark_corpus/structured_gold.jsonl','validation/SUCCESS_CRITERIA.json','validation/VALIDATION_RELEASE.json','benchmark_corpus/REAL_WORLD_BENCHMARK.md','benchmark_corpus/BLINDED_EXPERT_STUDY.md','scripts/run_benchmark_suite.py','scripts/run_mutation_benchmark.py','scripts/run_ablation_benchmark.py','frontend/index.html'
]
missing=[x for x in required if not (root/x).exists()]
if missing: print('Missing required files:',missing);sys.exit(1)

# Keep package metadata and the public runtime version synchronized without
# requiring tomllib (the project supports Python 3.10).
import re
_pyproject_text = (root/'pyproject.toml').read_text(encoding='utf-8')
_version_match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']\s*$', _pyproject_text)
if not _version_match:
    print('Could not read project.version from pyproject.toml');sys.exit(1)
project_version = _version_match.group(1)
from referee.version import __version__
if project_version != __version__:
    print('Version mismatch between pyproject.toml and referee/version.py:', project_version, __version__);sys.exit(1)

# The wheel ships a synchronized copy of runtime scientific assets. Refuse a
# release when the bundled copy diverges from the human-readable source tree.
asset_pairs = [
    ('core', 'referee/_assets/core'),
    ('agents', 'referee/_assets/agents'),
    ('skills', 'referee/_assets/skills'),
    ('guidelines', 'referee/_assets/guidelines'),
    ('profiles/guidelines', 'referee/_assets/profiles/guidelines'),
    ('profiles/domain_packs', 'referee/_assets/profiles/domain_packs'),
    ('config/profiles', 'referee/_assets/config/profiles'),
    ('config/benchmark_profiles', 'referee/_assets/config/benchmark_profiles'),
    ('config/journal_profiles', 'referee/_assets/config/journal_profiles'),
    ('frontend', 'referee/_assets/frontend'),
    ('benchmark_corpus', 'referee/_assets/benchmark_corpus'),
    ('schemas', 'referee/_assets/schemas'),
    ('validation', 'referee/_assets/validation'),
]
if hashlib.sha256((root/'config'/'defaults.json').read_bytes()).hexdigest() != hashlib.sha256((root/'referee'/'_assets'/'config'/'defaults.json').read_bytes()).hexdigest():
    print('Bundled runtime defaults are stale');sys.exit(1)

for src_rel, dst_rel in asset_pairs:
    src_root, dst_root = root/src_rel, root/dst_rel
    src_files = {p.relative_to(src_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in src_root.rglob('*') if p.is_file()}
    dst_files = {p.relative_to(dst_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in dst_root.rglob('*') if p.is_file()}
    if src_files != dst_files:
        print('Bundled runtime assets are stale:', src_rel)
        sys.exit(1)

json_docs={}
for folder in ('config','schemas'):
    for p in (root/folder).glob('*.json'):
        try:json_docs[str(p.relative_to(root))]=json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:print('Invalid JSON',p,e);sys.exit(1)
for folder in ('profiles','benchmark_profiles','journal_profiles'):
    for p in (root/'config'/folder).glob('*.json'):
        try: json.loads(p.read_text(encoding='utf-8'))
        except Exception as e: print('Invalid profile JSON',p,e);sys.exit(1)

from referee.contracts import concern_json_schema
if json.loads((root/'schemas'/'major_comment.schema.json').read_text(encoding='utf-8')) != concern_json_schema():
    print('major_comment.schema.json has drifted from canonical Concern model');sys.exit(1)
from referee.contracts import schemas as contract_schemas
if json.loads((root/'schemas'/'core_peer_review.schema.json').read_text(encoding='utf-8')) != contract_schemas.CORE_PEER_REVIEW_OUTPUT:
    print('core_peer_review.schema.json has drifted from runtime contract');sys.exit(1)
if json.loads((root/'schemas'/'independent_verifier.schema.json').read_text(encoding='utf-8')) != contract_schemas.VERIFIER:
    print('independent_verifier.schema.json has drifted from runtime contract');sys.exit(1)
try:
    import jsonschema
    for rel,obj in json_docs.items():
        if rel.startswith('schemas/'):jsonschema.Draft202012Validator.check_schema(obj)
except ImportError:print('Note: jsonschema not installed; schema meta-validation skipped.')

skills=sorted((root/'skills').glob('*/SKILL.md'));agents=sorted((root/'agents').glob('*.md'));mods=list((root/'referee').rglob('*.py'));tests=list((root/'tests').rglob('test_*.py'));profiles=list((root/'profiles'/'guidelines').glob('*.json'));domain_profiles=list((root/'profiles'/'domain_packs').glob('*.json'));config_profiles=list((root/'config'/'profiles').glob('*.json'));docx=list((root/'fixtures').rglob('*.docx'))
checks=[('skills',len(skills),56),('agents',len(agents),24),('runtime modules',len(mods),105),('tests',len(tests),40),('guideline profiles',len(profiles),15),('domain pack profiles',len(domain_profiles),8),('configuration profiles',len(config_profiles),5),('DOCX fixtures',len(docx),40)]
for label,n,min_n in checks:
    if n<min_n:print(f'Expected at least {min_n} {label}; found {n}');sys.exit(1)

def lines(p):return sum(1 for _ in p.open('r',encoding='utf-8'))
corpus={'scientific':lines(root/'benchmark_corpus'/'scientific_defect_cases.jsonl'),'revision':lines(root/'benchmark_corpus'/'revision_pairs.jsonl'),'rebuttal':lines(root/'benchmark_corpus'/'rebuttal_cases.jsonl'),'domain':lines(root/'benchmark_corpus'/'domain_science_cases.jsonl')}
if corpus['scientific']<400 or corpus['revision']<150 or corpus['rebuttal']<150 or corpus['domain']<250:print('Benchmark corpus below release floor',corpus);sys.exit(1)

compile_result=subprocess.run([sys.executable,'-m','compileall','-q',str(root/'referee'),str(root/'scripts'),str(root/'tests')],capture_output=True,text=True)
if compile_result.returncode:print(compile_result.stdout,compile_result.stderr);sys.exit(compile_result.returncode)
# Verify that current packaging metadata can actually produce an installable wheel.
import tempfile
with tempfile.TemporaryDirectory(prefix='referee-wheel-smoke-') as wheel_dir:
    wheel_result=subprocess.run([sys.executable,'-m','pip','wheel','.', '--no-deps','--no-build-isolation','-w',wheel_dir],cwd=root,capture_output=True,text=True)
    if wheel_result.returncode:
        print('Wheel build failed')
        print(wheel_result.stdout, wheel_result.stderr)
        sys.exit(wheel_result.returncode)
    built=list(Path(wheel_dir).glob('*.whl'))
    if len(built)!=1:
        print('Expected exactly one wheel from package smoke build; found',len(built));sys.exit(1)
test_result=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=root,capture_output=True,text=True);print(test_result.stdout.strip())
if test_result.returncode:print(test_result.stderr);sys.exit(test_result.returncode)
eval_result=subprocess.run([sys.executable,str(root/'scripts'/'run_evals.py')],cwd=root,capture_output=True,text=True)
if eval_result.returncode:print(eval_result.stdout,eval_result.stderr);sys.exit(eval_result.returncode)
eval_json=json.loads(eval_result.stdout)
if eval_json.get('passed')!=eval_json.get('total'):print('Evidence-lock eval did not fully pass');sys.exit(1)
if (eval_json.get('benchmark_readiness') or {}).get('valid_cases') != 1057:
    print('All 1,057 validation cases are not end-to-end-runner ready');sys.exit(1)
from referee.validation.release import verify_release_manifest
release_check=verify_release_manifest(root/'validation'/'VALIDATION_RELEASE.json')
if not release_check.get('valid'):
    print('Frozen validation release manifest is stale',release_check.get('errors'));sys.exit(1)
from referee.validation.adversarial import run_adversarial_integrity_suite
adv=run_adversarial_integrity_suite(root)
if adv.get('total')!=43 or adv.get('passed')!=43 or not adv.get('all_critical_pass') or adv.get('contract_test_pass_rate')!=1.0 or adv.get('deterministic_integrity_pass_rate')!=1.0:
    print('Adversarial contract/integrity suite failed',adv);sys.exit(1)
if adv.get('model_backed_adversarial_pass_rate') is not None:
    print('Offline adversarial suite must not claim model-backed behavioral coverage');sys.exit(1)
from referee.evals.ablations import ABLATIONS
required_ablations={'full_system','no_independent_verifier','no_evidence_entailment','no_steelman','no_redteam','no_literature_search','single_specialist','no_consensus','no_pairwise_prioritization'}
if {x.name for x in ABLATIONS} != required_ablations:
    print('Predeclared ablation set drifted');sys.exit(1)
gold_rows=[json.loads(x) for x in (root/'benchmark_corpus'/'structured_gold.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
if len(gold_rows)!=624 or len({r.get('case_id') for r in gold_rows})!=624:
    print('Structured hidden-gold coverage invalid',len(gold_rows));sys.exit(1)
for r in gold_rows:
    for k in ('defect_id','category','severity','required_mechanism_concepts','scientific_consequence','acceptable_resolutions'):
        if not r.get(k): print('Incomplete structured gold',r.get('case_id'),k);sys.exit(1)
# The one-command integrity campaign must complete without network/model calls.
import tempfile as _tempfile
with _tempfile.TemporaryDirectory(prefix='referee-validation-smoke-') as _td:
    vr=subprocess.run([sys.executable,'-m','referee.cli','validate','--suite','integrity','--output',_td,'--skip-source-tests'],cwd=root,capture_output=True,text=True)
    if vr.returncode:
        print('One-command integrity validation failed',vr.stdout,vr.stderr);sys.exit(vr.returncode)
    vs=json.loads((Path(_td)/'validation_summary.json').read_text(encoding='utf-8'))
    if vs.get('status')!='completed': print('Integrity campaign did not complete',vs);sys.exit(1)
# Zero-case full-campaign smoke test validates orchestration/output generation
# without pretending to measure scientific performance or making network calls.
with _tempfile.TemporaryDirectory(prefix='referee-full-campaign-smoke-') as _td:
    _env=dict(__import__('os').environ);_env['OPENAI_API_KEY']='offline-smoke-key'
    vr=subprocess.run([sys.executable,'-m','referee.cli','validate','--suite','full','--model','offline-smoke-model','--verifier-model','offline-smoke-verifier','--judge-model-a','offline-judge-a','--judge-model-b','offline-judge-b','--adjudicator-model','offline-adjudicator','--search-backend','none','--repeats','1','--limit-per-corpus','0','--output',_td,'--skip-source-tests'],cwd=root,capture_output=True,text=True,env=_env)
    if vr.returncode:
        print('Full validation orchestration smoke test failed',vr.stdout,vr.stderr);sys.exit(vr.returncode)
    required_outputs={'validation_summary.json','per_case_results.jsonl','metrics.csv','domain_metrics.csv','ablation_metrics.csv','repeatability_metrics.csv','citation_metrics.csv','failed_cases.jsonl','run_manifest.json','results_manifest.json','validation_report.html'}
    missing_outputs=sorted(x for x in required_outputs if not (Path(_td)/x).exists())
    if missing_outputs: print('Full validation smoke missing outputs',missing_outputs);sys.exit(1)

subprocess.run([sys.executable,str(root/'scripts'/'build_single_prompt.py')],check=True,capture_output=True,text=True)
dist=(root/'dist'/'BEIHANG_REFEREE_PROMPT.md').read_text(encoding='utf-8')
for p in skills:
    if p.read_text(encoding='utf-8').rstrip() not in dist:print('Portable prompt omits or truncates skill',p.relative_to(root));sys.exit(1)
manifest_path=root/'MANIFEST.json'
if manifest_path.exists():
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('skills')!=len(skills) or manifest.get('agents')!=len(agents) or manifest.get('runtime_modules')!=len(mods):print('Manifest counts stale');sys.exit(1)
checksum_path=root/'checksums.sha256'
if checksum_path.exists():
    for line in checksum_path.read_text().splitlines():
        if not line.strip():continue
        expected,rel=line.split(None,1);rel=rel.strip();p=root/rel
        if not p.exists():print('Checksum target missing',rel);sys.exit(1)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:print('Checksum mismatch',rel);sys.exit(1)
print('Package validation passed.')
print('Skills:',len(skills),'Agents:',len(agents),'Runtime modules:',len(mods),'Tests:',len(tests))
print('Guideline profiles:',len(profiles),'Domain pack profiles:',len(domain_profiles),'Configuration profiles:',len(config_profiles),'DOCX fixtures:',len(docx),'Benchmark corpus:',corpus)
print('Evidence-lock eval:',f"{eval_json['passed']}/{eval_json['total']}")
print('Portable prompt bytes:',len(dist.encode('utf-8')))
