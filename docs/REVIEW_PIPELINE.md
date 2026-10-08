# Beihang Referee Core Review Pipeline

Core Review Pipeline is the default initial-review architecture in Beihang Referee. It keeps the compact three-role design while restoring selected deterministic safeguards from the original full pipeline.

## Reasoning roles

1. **Core Reviewer** — maps the 5–12 scientifically important claims, creates manuscript evidence anchors, proposes bounded candidate concerns, and requests targeted evidence/specialist work.
2. **Specialist Executor** — one reusable role that loads only the skill family needed for a bounded proof burden.
3. **Independent Verifier** — receives a blinded scientific concern payload and tries to falsify it, including a strongest reasonable steelman favorable to the authors.

## Seven stages

`INGEST -> CORE_REVIEW -> TARGETED_EVIDENCE -> TARGETED_SPECIALISTS -> HARD_GATE -> INDEPENDENT_VERIFY -> FINALIZE`

### 1. Ingest
Safe intake, package inspection, and policy/security boundary.

### 2. Core review
Classification, claim registry, evidence anchors, candidate concerns, bounded literature queries, and specialist requests. Deterministic validation checks IDs/references and records malformed or contradictory core material.

### 3. Targeted evidence
Reporting/reproducibility audits and bounded scholarly retrieval. Every central novelty/SOTA claim must be covered by at least one bounded literature query. Unrelated search questions do not satisfy this requirement.

### 4. Targeted specialists
Specialists are claim-centered and capped by mode. Duplicate tasks are removed. Model-requested specialists are always merged with deterministic proof-burden requirements, so partial routing cannot silently omit an obvious specialist. Same-family tasks are merged, safety-critical tasks are ranked before the mode cap, and quantitatively dense manuscripts receive a high-priority numerical specialist trigger.

### 5. Hard evidence gate
Major concerns fail closed unless claims/anchors resolve, manuscript anchors pass integrity checks, closure criteria are actionable, and decisive external evidence is citation-verified. Near-duplicate concerns are collapsed. Novelty/prior-art accusations require opened, proposition-verified scholarly evidence regardless of the generator's own `external_verification_required` flag.

### 6. Independent verify
The verifier sees only the canonical scientific concern fields, frozen claims/anchors, claim-centered manuscript context, and additional contradiction-search context. It does **not** see generator/specialist identity, task IDs, hidden reasoning, or internal provenance metadata. It must affirm entailment, consequence proportionality, closure, and steelman survival.

### 7. Finalize
Provenance is recomputed. Verified concerns are ranked deterministically by **claim centrality × scientific consequence × verifier-adjusted confidence**. The final report exposes process-integrity gates, conservative scientific-readiness gates, verifier-independence status, literature/reproducibility/reporting/numerical status, and priority ranking. Scientific gates distinguish `NO_VERIFIED_BARRIER`, `NOT_ASSESSED`, `CONDITIONAL`, `FAIL`, and `N/A`; absence of a detected flaw is not represented as affirmative proof of soundness.

Optional post-freeze outputs:

- `--scorecard` — evidence-bound 50-dimension scorecard; cannot create new concerns and must use `N/A` when evidence is insufficient.
- `--target-journal "Journal Name"` — single-journal calibration after science is frozen.
- `--journal-profile profile.json` — frozen current official journal/publisher evidence for venue calibration.
- `--benchmark-profile <name-or-path>` — deterministic published-paper reference comparison after scorecard/calibration.
- `--verifier-model <model>` — optionally make concern verification cross-model rather than fresh-context/same-model.
- `exhaustive` — one fresh reassessment of the top verified concerns, without restoring the full audit pipeline's multi-trajectory default.

## Usage

```bash
referee review paper.pdf --pipeline core --mode deep --model <model>
referee review paper.pdf --pipeline core --mode deep --scorecard --target-journal "Nature" --model <model>
```

The broader full-audit pipeline is also available:

```bash
referee review paper.pdf --pipeline full --mode deep --model <model>
```

Recommended Core modes:

- `standard` — up to 1 targeted specialist.
- `deep` — up to 3 targeted specialists; recommended default.
- `exhaustive` — up to 6 targeted specialists plus one fresh reliability reassessment of the top verified concerns.

Core Review Pipeline is designed to reduce critic proliferation and orchestration overhead without weakening the evidence-locking rules that determine whether a major criticism is allowed to survive.
