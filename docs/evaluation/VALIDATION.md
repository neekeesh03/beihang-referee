# Beihang Referee validation and evaluation

Referee separates **software/integrity validation**, **model-backed scientific benchmarking**, and **human empirical validation**. Passing code tests does not establish scientific-review accuracy.

## Frozen validation protocol

Before official benchmark results are interpreted, `validation/VALIDATION_RELEASE.json` freezes hashes of the core review prompt, independent verifier prompt, benchmark judge/adjudicator prompts, JSON schemas, hidden structured gold, benchmark corpus, runtime code, defaults, and predeclared success criteria. A full campaign writes its exact models, search providers, temperature, randomness, repeat count, and ablation set to `run_manifest.json` **before the first model call**. That manifest is not rewritten after results exist. Result hashes are written separately to `results_manifest.json`.

Any material change to a frozen prompt, evaluator, hidden gold, scoring rule, model configuration, or runtime configuration belongs to a different experimental configuration. Prior scores are not retroactively replaced.

## Hard runtime integrity

A decisive concern is admitted only after canonical claim/anchor/concern identifiers resolve, quoted manuscript evidence resolves, external decisive evidence independently verifies, closure is testable, entailment supports the mechanism, a fresh independent verifier evaluates a frozen bundle, and post-verification hashes remain unchanged. Duplicate canonical IDs, missing references, invalid provenance, missing verification, identity collisions, schema-invalid scientific state, and frozen-state mutations are **hard invariants**. A hard failure sets `status=failed_validation` and `final_review_exportable=false`; such a run cannot be frozen as a successful handoff.

## Structured hidden-gold evaluation

The scientific/domain corpora contain 624 planted defects with structured hidden gold. Each defect records mechanism concepts, severity, consequence, acceptable resolution, and forbidden misdiagnoses. Gold is revealed only after the manuscript review finishes.

Successful detection is **not** based on lexical/category similarity. Each predicted concern is evaluated against hidden structured gold through:

1. a recorded deterministic concept screen;
2. blinded independent Judge A;
3. blinded independent Judge B;
4. an adjudicator when judgments disagree.

Judges receive the predicted concern and hidden structured gold, not Referee configuration, aggregate results, or desired outcomes. Official campaigns record judge/adjudicator model and fresh context identities. Mechanism, consequence, severity, and resolution are scored separately.

## Citation integrity

External citations are verified independently of model self-report. Referee records source existence, bibliographic identity, source-content availability, and whether retrieved content supports the proposition for which the source was used. Fabricated references, metadata mismatches, unsupported real citations, and unverifiable citations are reported separately. Decisive novelty/contradiction evidence must pass existence + metadata + opened-content + proposition-support checks.

## Revision and rebuttal closure

Revision/rebuttal benchmarks score scientific closure rather than response formatting. They distinguish `resolved`, `partially_resolved`, `unresolved`, and `not_assessable`, plus false closure, missed closure, promise-without-change, response-without-evidence, and new-regression detection. A scientifically sufficient narrowed claim may close an unnecessary experimental request; persuasive response prose without manuscript evidence does not.

## Counterfactual sensitivity

Defect→repair pairs are a headline metric. The target concern must appear in the defective version and disappear after a scientifically sufficient repair while unrelated concerns remain stable. Metrics include defect detection, repair recognition, causal-sensitivity pass rate, persistent false-concern rate, and unrelated-concern stability.

## Repeatability

Repeated runs distinguish:

- `stable_true_positive`;
- `unstable_true_positive`;
- `stable_false_positive`;
- `unstable_false_positive`;
- stable true negatives and false negatives.

Stable false positives are reported explicitly because repeated error is not evidence of correctness.

## Architecture ablations

The frozen ablation set is:

- `full_system`;
- `no_independent_verifier`;
- `no_evidence_entailment`;
- `no_steelman`;
- `no_redteam`;
- `no_literature_search`;
- `single_specialist`;
- `no_consensus`;
- `no_pairwise_prioritization`.

The evaluator and benchmark stay fixed while the architecture changes. Precision, recall, ccore-control false positives, mechanism accuracy, severity, citations, cost, and latency are reported per configuration.

## Predeclared success criteria

`validation/SUCCESS_CRITERIA.json` was written before official benchmark results. Primary metrics remain visible separately; there is no opaque overall score. The primary metrics are major-concern precision, scientific-defect recall, ccore-control false-positive rate, mechanism accuracy, counterfactual sensitivity, anchor integrity, and citation-support accuracy. Secondary metrics include severity macro-F1, closure/consequence correctness, repeatability, stable false positives, calibration, latency/cost, and domain recall.

## One-command campaign

Deterministic integrity only:

```bash
referee validate --suite integrity --output validation-results
```

Complete model-backed campaign:

```bash
referee validate --suite full --model "$REFEREE_MODEL" --repeats 3 --output validation-results
```

Optional `--verifier-model`, `--judge-model-a`, `--judge-model-b`, and `--adjudicator-model` let the benchmark use distinct capable model families where available. `--limit-per-corpus` is for development smoke tests only; omit it for an official campaign.

Required outputs include `validation_summary.json`, `per_case_results.jsonl`, `metrics.csv`, `domain_metrics.csv`, `ablation_metrics.csv`, `repeatability_metrics.csv`, `citation_metrics.csv`, `failed_cases.jsonl`, immutable `run_manifest.json`, and `results_manifest.json`; an HTML report is generated for convenience.

## Adversarial integrity suite

Before the expensive benchmark, Referee executes 43 deterministic attacks spanning evidence provenance, identifier collisions, frozen-state mutation, benchmark gaming, reviewer-behaviour errors, citation/literature attacks, prompt injection, and revision/rebuttal closure. Critical deterministic integrity properties target 100% pass.

## Real-paper and blinded expert evaluation

`benchmark_corpus/REAL_WORLD_BENCHMARK.md` defines an atomic expert-adjudicated real-paper benchmark. `benchmark_corpus/BLINDED_EXPERT_STUDY.md` defines source-blinded human rating of factual correctness, evidence grounding, scientific importance, severity, actionability, redundancy, usefulness, and inclusion in a real review. The repository provides protocols/tooling but does **not** fabricate human judgments or model-backed scientific performance results.
