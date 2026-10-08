from pathlib import Path

root = Path(__file__).resolve().parents[1]

full_core_order = [
    'core/PEER_REVIEW_PROMPT.md',
    'core/INDEPENDENT_VERIFIER_PROMPT.md',
    'core/AGENT_SYSTEM.md',
    'core/POLICY_GATE.md',
    'core/INPUT_CONTRACT.md',
    'core/EVIDENCE_DISCIPLINE.md',
    'core/CLAIM_BURDEN_MATRIX.md',
    'core/LITERATURE_SEARCH_PROTOCOL.md',
    'core/VALIDATION_LADDER.md',
    'core/BENCHMARK_EPISTEMOLOGY.md',
    'core/CLAIM_LANGUAGE_CALIBRATION.md',
    'core/SEVERITY_ACTIONABILITY.md',
    'core/REVIEW_RELIABILITY_PROTOCOL.md',
    'workflow/PIPELINE.md',
    'guidelines/REPORTING_GUIDELINE_ROUTER.md',
    'core/SCORECARD.md',
    'core/TEN_JOURNAL_ENGINE.md',
    'core/OUTPUT_CONTRACT.md',
]

core_pipeline_order = [
    'core/CORE_REVIEWER_PROMPT.md',
    'core/SPECIALIST_EXECUTOR_PROMPT.md',
    'core/CORE_VERIFIER_PROMPT.md',
    'core/DIAGNOSTIC_SCORECARD_PROMPT.md',
    'core/TARGET_JOURNAL_CALIBRATOR_PROMPT.md',
    'core/POLICY_GATE.md',
    'core/INPUT_CONTRACT.md',
    'core/EVIDENCE_DISCIPLINE.md',
    'core/CLAIM_BURDEN_MATRIX.md',
    'core/LITERATURE_SEARCH_PROTOCOL.md',
    'core/VALIDATION_LADDER.md',
    'core/BENCHMARK_EPISTEMOLOGY.md',
    'core/CLAIM_LANGUAGE_CALIBRATION.md',
    'core/SEVERITY_ACTIONABILITY.md',
    'workflow/PIPELINE.md',
    'guidelines/REPORTING_GUIDELINE_ROUTER.md',
    'core/SCORECARD.md',
    'core/OUTPUT_CONTRACT.md',
]


def build(title: str, core_order: list[str], output_name: str) -> None:
    parts = [f'# {title}\n']
    for rel in core_order:
        p = root / rel
        parts.append(f'\n\n---\n\n## SOURCE: {rel}\n\n')
        parts.append(p.read_text(encoding='utf-8').rstrip() + '\n')

    parts.append('\n\n---\n\n# Reviewer role library\n')
    for p in sorted((root / 'agents').glob('*.md')):
        rel = p.relative_to(root)
        parts.append(f'\n\n## SOURCE: {rel}\n\n')
        parts.append(p.read_text(encoding='utf-8').rstrip() + '\n')

    parts.append('\n\n---\n\n# Complete specialist skill library\n')
    for p in sorted((root / 'skills').glob('*/SKILL.md')):
        rel = p.relative_to(root)
        parts.append(f'\n\n## SOURCE: {rel}\n\n')
        parts.append(p.read_text(encoding='utf-8').rstrip() + '\n')

    out = root / 'dist' / output_name
    out.parent.mkdir(exist_ok=True)
    out.write_text(''.join(parts), encoding='utf-8')
    print(out)


build('Beihang Referee — Portable Core Review Prompt', core_pipeline_order, 'BEIHANG_REFEREE_PROMPT.md')
build('Beihang Referee — Portable Full Audit Prompt', full_core_order, 'BEIHANG_REFEREE_FULL_AUDIT_PROMPT.md')
