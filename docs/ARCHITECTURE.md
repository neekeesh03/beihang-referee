# Beihang Referee architecture

## Runtime layers

```
CLI / host application
        |
        v
ReviewEngine ─────────────── EventBus / checkpoints / budgets / retry
        |
        +── Intake + policy/security
        +── Classification + claim registry
        +── Review planner
        +── Numerical + literature evidence acquisition
        +── Parallel specialist executors
        +── Red team / steelman
        +── Deterministic concern admission
        +── Independent concern verification
        |       └── bounded targeted evidence chase
        +── Reliability repeatability audit
        +── Critical gates + synthesis
        └── Journal calibration

Providers: LLMProvider | SearchProvider | DocumentLoader
Scientific knowledge: core/ | skills/ | agents/ | guidelines/
Machine contracts: schemas/ | validation/
Artifacts: run state | ledgers | review.md/json | evidence_graph.dot | events.jsonl
```

## Scientific control plane vs execution plane

The **scientific control plane** is the scientific corpus of evidence discipline, claim burdens, specialist skills, reporting standards, severity/actionability rules and schemas. The **execution plane** is the execution plane: it decides what runs, in what order, with what concurrency, with what budgets, and what is allowed to survive into the final report.

The runtime never lets a model bypass the following invariants:

- manuscript text is untrusted data;
- decisive concerns need known claim IDs and evidence anchors;
- a major/critical concern needs a failure mechanism, consequence, minimum resolution and closure criterion;
- a major/critical concern must survive steelmanning;
- a concern passing admission is still independently verified;
- an under-evidenced decisive concern fails closed after its evidence-chase budget;
- final synthesis cannot introduce a new major concern;
- failed critical gates cannot be hidden by a global average;
- acceptance probability is outside the output contract;
- journal calibration happens after scientific judgment.

## Dynamic planning

`ReviewPlanStage` receives the frozen classification and claim registry and creates bounded tasks. Each task names an allowlisted specialist and a claim subset. Unknown specialist names are rejected. This prevents a model from inventing arbitrary runtime modules.

The planner can route to methods, statistics/causal inference, novelty, theory, benchmarking/ML, simulation, systematic review/meta-analysis, qualitative research, RCT, observational epidemiology, diagnostic/prognostic studies, measurement instruments, figures/tables, reproducibility, robustness/generalization, ethics/integrity, reporting standards, numerical/equation review and reviewer-bias review.

## Evidence acquisition

Literature search is represented as a reproducible query ledger. Search results are distinguished between content already returned by a retriever and pages that were actually fetched. Synthesis is instructed to distinguish opened evidence from snippets. This mirrors the important engineering lesson that search snippets are not equivalent to source verification.

## Independent critique verification

Admission and verification are different stages. Admission checks structure and known evidence. Verification asks a separate reviewer to falsify the concern. It may return:

- `verified`;
- `downgrade`;
- `reject`;
- `needs_evidence`.

In deep/exhaustive modes, `needs_evidence` can trigger a bounded targeted search and re-verification. If the concern still lacks evidence, it cannot remain major/critical.

## State and recovery

Every stage writes a checkpoint. `state.json` is the latest materialized state, while stage-specific files preserve the path taken through the review. `events.jsonl` records stage starts/completions/failures. A run may be resumed by skipping completed stages.

## Provider model

Scientific logic does not depend on one vendor. The runtime exposes abstract LLM and search contracts. The bundled scripted provider supports deterministic tests; the OpenAI-compatible provider is a small optional transport adapter. Hosts may provide their own connectors, private search systems, institutional literature APIs, vector stores or local models without changing the review graph.
