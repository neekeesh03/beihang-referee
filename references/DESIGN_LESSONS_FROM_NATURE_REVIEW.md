# Design lessons extracted from the supplied Nature peer-review workflow

The user supplied a multi-round Nature peer-review file for a computational/AI systems manuscript. This package uses it as an empirical example of reviewer reasoning, not as a universal Nature checklist.

Key design lessons encoded into the design:

1. **Benchmark epistemology:** a benchmark score is not enough; reviewers ask what capability the benchmark actually measures.
2. **Development/evaluation coupling:** reproduction of tutorial/reference outputs can demonstrate reuse while still falling short of independent generalization or scientific reasoning.
3. **Baseline freshness:** in fast-moving fields, the comparator can become outdated during revision, changing the significance of the contribution.
4. **Performance attribution:** performance gains must be attributed to architecture vs information access, preprocessing, compute, curation or scaffolding.
5. **Minimal-sufficient alternative:** complex architecture should be compared with simpler plausible solutions.
6. **Ablation:** component necessity should be tested, not assumed.
7. **End-to-end reliability:** conditional accuracy among successful cases should not obscure failures before evaluation.
8. **Failure taxonomy:** characterize failure frequency, severity, detectability and recoverability.
9. **Ground-truth validity:** manual grading requires transparent rubrics and agreement/independence where relevant.
10. **Validation provenance:** secondary analysis of existing experiments is not automatically equivalent to new experimental validation.
11. **Human-contribution accounting:** claims of autonomous discovery should disclose consequential human selection and interpretation steps.
12. **Claim-language calibration:** “discovered,” “identified,” “validated,” “causal,” “generalizes,” and “robust” require evidence proportional to wording.
13. **Temporal robustness:** software/API/model improvements can erode a contribution; durability matters.
14. **Venue-contribution matching:** strong engineering can still be below the conceptual threshold of a broad venue while being excellent for a methods/specialist venue.
15. **Revision adjudication:** authors can add requested experiments yet leave the underlying epistemic concern unresolved; closure criteria matter.
16. **Reviewer disagreement:** specialists can agree on facts and still disagree on significance or venue threshold; a meta-reviewer should classify the source of disagreement rather than averaging scores.

See `references/raw_user_material/nature_peer_review_workflow.pdf` for the supplied source document.
