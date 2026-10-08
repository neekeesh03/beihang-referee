# Beihang Referee validation contract

This directory freezes Referee's evaluation protocol before official model-backed benchmark results are interpreted. `SUCCESS_CRITERIA.json` is predeclared. `VALIDATION_RELEASE.json` hashes the review/verifier/evaluator prompts, schemas, hidden gold, benchmark corpus, scientific runtime, success criteria and configuration.

Validation deliberately distinguishes three adversarial layers:

1. **Static contract tests** — required instructions, schemas and security boundaries exist.
2. **Deterministic integrity tests** — IDs, hashes, provenance, anchors and state invariants behave correctly.
3. **Model-backed behavioral attacks** — actual review/rebuttal workflows are executed against missing-reporting, optional-experiment, noncausal, prompt-injection and promise-without-change attacks.

The first two can run offline with `referee validate --suite integrity`. The third is executed before the expensive benchmark in `referee validate --suite full` and is reported separately; static prompt checks never count as behavioral evidence.

Every full campaign records an evaluator-independence classification. Same-model fresh-context judging is labeled **internal validation**, never independent external validation. Use `--require-independent-evaluation` when an external validation claim requires at least cross-model judging.

Changing any frozen component requires regenerating the frozen manifest **before** official results are inspected. Prior result manifests are not overwritten.

## Validation scope

The default core review pipeline is covered by source tests, deterministic integrity/adversarial checks, runtime regression tests, synthetic benchmark cases, and frozen protocol/code hashes.

The model-backed architecture-ablation campaign exercises the broader full-audit pipeline because those ablations target stages such as red-team/steelman review, independent trajectories, and pairwise prioritization. Results from that campaign must not be silently attributed to the core pipeline. A formal model-backed or human-expert benchmark of the core pipeline remains a separate empirical exercise.

Regenerating the frozen validation manifest verifies software/protocol identity only; it does not manufacture real-paper or human-review validity.
