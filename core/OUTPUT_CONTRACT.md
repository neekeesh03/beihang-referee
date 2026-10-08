# Output Contract

## Default visible output: progressive disclosure

### Layer A — Decision brief

- review context / policy status;
- inferred field, article type, and study design with confidence;
- central contribution in 2–5 sentences;
- strongest supported result(s);
- 1–5 decisive concerns, if any;
- reviewer-confidence and stability status;
- what is established / plausible / not established.

### Layer B — Evidence-locked major comments

Every major comment must include:

- unique concern ID;
- post-validity priority (P0/P1/P2 or pairwise ranking), assigned only after the concern is scientifically validated;
- exact evidence anchor(s);
- affected claim ID(s);
- issue and mechanism;
- scientific consequence;
- minimum resolution;
- closure criterion;
- numeric reviewer confidence in [0,1];
- explicit steelman, steelman-survival status, and survival reason;
- provenance-gate status;
- independent-verification identity/hash record.

### Layer C — Scientific audit appendices

Include relevant modules only:

- document and version map;
- claim registry / claim–evidence graph;
- literature search ledger and nearest prior art;
- novelty / knowledge delta;
- theory / mechanism / rival theory;
- design / measurement / statistics / causal inference;
- benchmark / model validation;
- numerical, equation, figure, table, and cross-file consistency;
- robustness / generalization;
- code/data/reproducibility;
- ethics/integrity/privacy;
- reporting and domain standards;
- red-team / steelman;
- reliability/disagreement audit;
- critical gates and optional diagnostic scorecard.

### Layer D — Venue calibration

- evidence-supported journal set (target up to 10; never pad);
- official current scope source when externally verified;
- recent comparable work where available;
- scientific alignment and key gap;
- revision-to-venue implications.

### Layer E — Journal-ready report

- opening assessment;
- manuscript-specific strengths;
- prioritized major comments;
- minor comments;
- developmental assessment;
- minimum path to claim-level publishability;
- confidential-editor note only when contextually appropriate and policy-compliant.

## Full exhaustive audit

The system may still generate the full-style comprehensive audit, but sections that are N/A or low-information should be omitted rather than filled mechanically.

## Prohibited output behavior

- no unsupported major concern;
- no invented anchor, citation, policy, or journal criterion;
- no overall numeric acceptance probability;
- no forced mean score across heterogeneous dimensions;
- no padded journal list;
- no hidden decisive criticism confined to editor-only text;
- no “new experiment wish list” presented as mandatory without claim-level necessity.
