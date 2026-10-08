from __future__ import annotations
from ..models import ReviewState


def render_review_markdown(state: ReviewState) -> str:
    fr = state.final_review or {}
    brief = fr.get("decision_brief", {})
    lines = [
        "# Scientific Peer Review",
        "",
        f"**Run:** `{state.run_id}`  ",
        f"**Mode:** `{state.mode}`  ",
        f"**Status:** `{state.status}`",
        "",
        "## Decision brief",
    ]
    if isinstance(brief, dict):
        for k, v in brief.items():
            lines.append(f"- **{k.replace('_',' ').title()}:** {v}")
    else:
        lines.append(str(brief))
    lines += ["", "## Major concerns"]
    if not state.admitted_concerns:
        lines.append("No major/critical concern passed the evidence-lock admission gate.")
    for i, c in enumerate(state.admitted_concerns, 1):
        lines += [
            "",
            f"### {i}. {c.get('title','Untitled concern')}",
            f"**Severity:** {c.get('severity')}  ",
            f"**Affected claims:** {', '.join(c.get('claim_ids', []))}  ",
            f"**Evidence anchors:** {', '.join(c.get('evidence_anchor_ids', []))}",
            "",
            f"**Failure mechanism.** {c.get('failure_mechanism','')}",
            "",
            f"**Scientific consequence.** {c.get('scientific_consequence','')}",
            "",
            f"**Minimum resolution.** {c.get('minimum_resolution','')}",
            "",
            f"**Closure criterion.** {c.get('closure_criterion','')}",
        ]
    minor = fr.get("minor_comments") or []
    if minor:
        lines += ["", "## Minor comments"] + [f"- {x if isinstance(x,str) else x.get('text',x)}" for x in minor]
    if state.critical_gates:
        lines += ["", "## Critical gates"]
        for group, gates in state.critical_gates.items():
            lines.append(f"### {group.replace('_',' ').title()}")
            if isinstance(gates, dict):
                for k, v in gates.items():
                    if k == "_status_semantics":
                        continue
                    if isinstance(v, dict):
                        lines.append(
                            f"- **{k.replace('_',' ').title()}:** {v.get('status')} — {v.get('basis','')}"
                            + (f" _(assessed by: {', '.join(v.get('assessed_by') or [])})_" if v.get('assessed_by') else "")
                        )
                    else:
                        lines.append(f"- **{k}:** {v}")
            else:
                lines.append(str(gates))
    scorecard = fr.get("diagnostic_scorecard") or {}
    if isinstance(scorecard, dict) and scorecard.get("dimensions"):
        lines += ["", "## Diagnostic scorecard"]
        if scorecard.get("measurement_status"):
            lines.append(f"- **Measurement status:** {scorecard.get('measurement_status')}")
        if scorecard.get("precision_warning"):
            lines.append(f"- **Precision warning:** {scorecard.get('precision_warning')}")
        for row in scorecard.get("dimensions") or []:
            if isinstance(row, dict):
                basis = row.get("evidence_basis") or []
                suffix = f" Evidence: {', '.join(str(x) for x in basis)}" if basis else ""
                score_text = row.get('score','N/A')
                score_label = f"{score_text}/10" if score_text != "N/A" else "N/A"
                lines.append(
                    f"- **{row.get('dimension','')}:** {score_label} — "
                    f"{row.get('justification','')} (confidence {row.get('confidence','')}).{suffix}"
                )
        if scorecard.get("calibration_note"):
            lines += ["", f"_{scorecard.get('calibration_note')}_"]
    target = fr.get("target_journal_calibration") or {}
    if isinstance(target, dict) and target:
        lines += ["", "## Target-journal calibration"]
        for key in (
            "target_journal", "fit_score", "impact_potential_score", "publication_readiness_score",
            "audience_fit", "contribution_threshold", "major_mismatch", "evidence_status",
            "profile_source_count", "confidence",
        ):
            if key in target:
                lines.append(f"- **{key.replace('_',' ').title()}:** {target.get(key)}")
    benchmark = fr.get("benchmark_comparison") or {}
    if isinstance(benchmark, dict) and benchmark:
        lines += ["", "## Benchmark comparison"]
        lines.append(f"- **Profile:** {benchmark.get('label') or benchmark.get('profile_id')}")
        lines.append(f"- **Sample size:** {benchmark.get('sample_size')}")
        lines.append(f"- **Informal calibration only:** {benchmark.get('informal_calibration_only')}")
        for metric, row in (benchmark.get("metrics") or {}).items():
            if isinstance(row, dict):
                lines.append(
                    f"- **{metric.replace('_',' ').title()}:** current {row.get('current')} | "
                    f"q25 {row.get('q25')} | median {row.get('median')} | percentile {row.get('percentile')} | {row.get('status')}"
                )
    submission = fr.get("submission_state") or (brief.get("scientific_state") if isinstance(brief, dict) else None)
    if isinstance(submission, dict) and submission:
        lines += ["", "## Submission state", f"**{submission.get('status')}** — {submission.get('rationale','')}"]

    if state.reliability:
        lines += ["", "## Review reliability", f"{state.reliability}"]
    if state.journal_landscape:
        lines += ["", "## Journal landscape"]
        for j in state.journal_landscape:
            if isinstance(j, dict):
                lines.append(f"- **{j.get('journal', j.get('name',''))}** — {j.get('rationale','')}")
            else:
                lines.append(f"- {j}")
    if state.warnings:
        lines += ["", "## Validation warnings"] + [f"- {w}" for w in state.warnings]
    lines += ["", "## Run metrics", f"`{state.metrics}`", ""]
    return "\n".join(lines)
