# Formal Review AI-Policy Gate

This gate runs before manuscript analysis.

## Why this exists

Current publisher policies differ. Several publishers prohibit formal peer reviewers from uploading unpublished manuscripts into generative-AI systems or using AI to generate the scientific review. The agent must not imply that such use is permitted when it is not.

## Context classification

Infer one of the following without asking unless absolutely necessary:

### A. AUTHOR-SIDE / OWNER DIAGNOSTIC
The user appears to be an author, collaborator, editor with authorization, or owner of the material, or explicitly asks for a simulated review of their own manuscript.

**Action:** Full agent workflow may proceed, subject to data/privacy constraints.

### B. PUBLIC-MANUSCRIPT AUDIT
The material is already public (published paper, public preprint, public repository).

**Action:** Full workflow may proceed. Clearly distinguish post-publication analysis from confidential peer review.

### C. FORMAL CONFIDENTIAL REVIEW — POLICY PERMITS APPROVED AI
The user explicitly states they are an invited reviewer/editor and the applicable journal/publisher currently permits the intended AI use in an approved/private environment.

**Action:** Proceed only within the verified policy conditions. Include required AI-use disclosure text if the policy requires it.

### D. FORMAL CONFIDENTIAL REVIEW — POLICY RESTRICTS/PROHIBITS AI INGESTION OR JUDGMENT
The user explicitly states they are a reviewer/editor and current publisher/journal policy prohibits uploading manuscript content to generative AI or prohibits AI-generated scientific assessment.

**Action:** Do not ingest/analyze confidential manuscript content through the AI workflow. Provide only a non-manuscript-specific review checklist or explain how to perform the review manually. Do not work around the restriction.

### E. FORMAL REVIEW STATUS UNKNOWN
No target journal or reviewer role is stated.

**Default:** Treat the task as an **author-side/public-style manuscript diagnostic**, not as an official confidential journal review. State this only when relevant to output use. Do not ask the user to choose a journal.

## Live policy verification

When web access is available and formal review is implicated:

1. verify the current journal-specific instructions first;
2. then verify publisher-wide policy;
3. use the stricter applicable rule;
4. record source and date checked;
5. never rely only on a cached package summary for high-stakes confidentiality decisions.

See `guidelines/PUBLISHER_POLICY_REGISTRY.md`.
