# LLM peer-review design notes

The architecture incorporates several broad lessons from recent LLM-assisted peer-review research discussed during prompt development:

- generic “review this paper” prompts under-specify the task;
- paper-specific/aspect-specific questions improve specificity and coverage;
- specialized reviewer roles can reduce generic commentary;
- literature retrieval improves grounding;
- scores can be sensitive to prompt wording and should use anchored rubrics;
- manuscript-side prompt injection is a real risk for AI reviewers;
- AI review should not be treated as equivalent to human expert accountability.

Representative research families to verify/update when maintaining the package include ReviewerGPT, Reviewer2, MARG, large-scale LLM-review comparison studies, and newer LLM-as-reviewer robustness/prompt-injection benchmarks. This file is a design note, not a frozen bibliography; current literature should be re-searched during future package updates.
