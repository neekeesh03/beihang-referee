# Beihang Referee Review Pipelines

The runtime in `referee/stages/` is authoritative for execution order. Scientific contracts in `core/`, `skills/`, and `guidelines/` are authoritative for judgment criteria.

## Default initial review: Core Review Pipeline

The default initial-review pipeline contains seven stages:

1. `C01_ingest` — safe intake, package inspection, policy/security boundary.
2. `C02_core_review` — classification, 5–12 central/supporting claims, evidence anchors, bounded candidate concerns, literature queries, and specialist requests. Deterministic validation checks the core output.
3. `C03_targeted_evidence` — reporting/reproducibility audits and bounded scholarly search. Every central novelty/SOTA claim must have a covering literature query.
4. `C04_targeted_specialists` — capped targeted specialists after merging model requests with deterministic required families, same-family task merging, proof-burden ranking, and a high-priority quantitative/numerical safety trigger.
5. `C05_hard_evidence_gate` — ID/anchor/closure/citation validation, near-duplicate concern suppression, and fail-closed novelty/prior-art verification.
6. `C06_independent_verify` — blinded fresh-context adversarial verification with claim-centered plus contradiction-search manuscript context.
7. `C07_finalize` — provenance recomputation, consequence-aware deterministic ranking, conservative process/scientific gates, verifier-independence reporting, audit status, and optional post-freeze evidence-bound scorecard, journal calibration, and benchmark comparison.

### Core admission rule

A major concern can reach the final report only when:

- its claim IDs and evidence anchors resolve;
- manuscript anchors pass deterministic integrity checks;
- decisive external evidence is opened and independently citation/proposition verified;
- novelty/prior-art allegations include verified external scholarly evidence;
- its closure criterion is actionable/testable;
- it is not a near-duplicate of a stronger equivalent concern;
- a fresh independent verifier affirms claim mapping, evidence entailment, consequence proportionality, sufficient resolution, testable closure, and steelman survival;
- no manuscript contradiction defeats the criticism;
- frozen manuscript/claim/anchor/concern hashes remain consistent through export.

The verifier is intentionally blind to generator identity, specialist identity, task IDs, and hidden provenance metadata.

## Full Audit Pipeline

`--pipeline full` enables the broader multi-stage architecture for heavy audit use and architecture comparisons. It includes separate planning, numerical, literature, specialist, red-team/steelman, provenance/entailment, independent trajectories when configured, pairwise priority, reliability, synthesis, and journal-calibration stages.

Full Audit is **not** the default initial-review path because the additional critic/trajectory layers can increase cost and critic proliferation. The default core pipeline keeps the high-value deterministic safeguards without requiring those additional layers.

## Optional Core diagnostics

`--scorecard` runs the 50-dimension diagnostic scorecard after the scientific state is frozen. It receives a frozen dimension evidence bundle and must use `N/A` when evidence is insufficient. Scores cannot admit new concerns and a failed gate cannot be averaged away.

`--target-journal "..."` performs a single-target venue calibration after scientific judgments are frozen. `--journal-profile profile.json` can supply current official journal/publisher evidence. Without that profile, calibration is explicitly provisional and confidence is capped.

`--benchmark-profile <name-or-path>` compares the frozen summary scores to a user-owned reference distribution. Benchmark comparison is deterministic and cannot modify scientific concerns. Cross-configuration profiles may be displayed but are prevented from changing submission state unless explicitly marked suitable for decision support.

## Runtime artifacts

Core can emit:

- `document_map.json` and package/reporting/reproducibility audits;
- `core_review.json`;
- `core_search_ledger.json` when search runs;
- `core_specialist_results.json`;
- `core_hard_gate.json`;
- `core_independent_verification.json`;
- `core_final_review.json`;
- `concern_admission_log.json`;
- `evidence_graph.dot`;
- `review.json`, `review.md`, and optional HTML/CSV outputs;
- stage checkpoints, events, run state, and validation status.
