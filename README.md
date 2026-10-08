# Beihang Referee

**Evidence-grounded, auditable AI-assisted review for scientific manuscripts.**

Beihang Referee is an open-source review engine that separates scientific criticism from the model that proposes it. Instead of treating an LLM response as a finished peer review, Referee builds a claim/evidence state, routes targeted checks, applies deterministic admission rules, and independently verifies major concerns before they can appear in the final review.

> **Core rule:** no decisive judgment without a traceable evidence path, and no major criticism without a testable closure path.

Beihang Referee is independent student-developed research software. It is **not** an official service of Beihang University and is **not** a replacement for expert scientific judgment.

## Why this project exists

A plausible-sounding critique is not necessarily a valid critique. Referee is designed around that failure mode.

```text
manuscript / supplement / data / code
                  │
                  ▼
        ┌────────────────────┐
        │ safe ingestion     │
        │ + package audit    │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ core claim review  │
        │ + evidence anchors │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ targeted evidence  │
        │ + specialists      │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ deterministic hard │
        │ evidence gate      │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ independent        │
        │ adversarial check  │
        └─────────┬──────────┘
                  ▼
        review.md / JSON / HTML / CSV / evidence graph
```

A major concern is expected to identify the affected claim, point to evidence, explain the failure mechanism and scientific consequence, propose the minimum sufficient resolution, define a closure criterion, and survive independent verification.

## Try it without an API key

The repository includes a deterministic offline demo so you can inspect the workflow before configuring any model provider.

```bash
python -m pip install -e '.[office,pdf,validation]'

referee review examples/demo_manuscript.md \
  --pipeline core \
  --mode standard \
  --provider scripted \
  --scripted-responses examples/demo_responses.json \
  --search-backend none \
  --run-id demo

cat runs/demo/artifacts/review.md
```

The expected output is also checked into [`examples/expected_demo_review.md`](examples/expected_demo_review.md).

For the shortest setup path, see [`QUICKSTART.md`](QUICKSTART.md).

## Run a real review

Create an environment and install the common manuscript extras:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[office,pdf,scholarly,validation]'
```

Configure an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY="..."
export REFEREE_MODEL="<model-id>"
# Optional: a separate verifier model
export REFEREE_VERIFIER_MODEL="<verifier-model-id>"
```

Run the default review pipeline:

```bash
referee review manuscript.pdf --mode deep --model "$REFEREE_MODEL"
```

To disable all external scholarly retrieval explicitly:

```bash
referee review manuscript.pdf --mode deep --search-backend none --model "$REFEREE_MODEL"
```

Referee prints the path to the generated `review.md` when the run completes.

## Review pipeline

The core pipeline uses seven stages and three reasoning roles:

1. **Ingest** — safe manuscript/package intake, structural inspection, and the security boundary.
2. **Core review** — classify the study, register important claims, anchor evidence, propose bounded concerns, and request targeted checks.
3. **Targeted evidence** — reporting/reproducibility inspection plus bounded literature retrieval when enabled.
4. **Targeted specialists** — route only the specialist families justified by the manuscript and proof burden.
5. **Hard evidence gate** — validate claim references, anchors, confidence, closure tests, citation support, provenance, and near-duplicate concerns.
6. **Independent verification** — send a blinded scientific payload to a fresh adversarial verifier and search for author-favorable counterevidence.
7. **Finalize** — freeze the verified concern set, compute conservative readiness gates, and export the review artifacts.

The three model-facing roles are **Core Reviewer**, **Specialist Executor**, and **Independent Verifier**. An optional **Full Audit Pipeline** is available with `--pipeline full` for broader audit-oriented workflows.

See [`docs/REVIEW_PIPELINE.md`](docs/REVIEW_PIPELINE.md) and [`docs/architecture/OVERVIEW.md`](docs/architecture/OVERVIEW.md) for the detailed design.

## What makes Referee different

### Fail-closed major-comment admission

A model cannot promote a criticism to a final major concern simply by sounding convincing. Major concerns must satisfy machine-checkable evidence and closure requirements before independent verification.

### Claim-centered evidence state

Referee maintains canonical claim IDs, evidence-anchor IDs, provenance, hashes, concern states, verification outcomes, and finalization records so the review can be inspected after generation.

### Independent falsification, not self-approval

The verifier receives a reduced scientific payload rather than hidden generator identity or provenance internals. You can also select a distinct verifier model with `--verifier-model`.

### Fail-closed novelty and citation handling

Manuscript text alone cannot prove that prior art exists. Decisive novelty/prior-art criticism requires opened scholarly evidence. Citation existence/metadata and proposition support are treated as separate questions.

### Closure-oriented review

A major criticism must specify not only what is wrong but what would count as resolving it. This makes Referee useful for revision and rebuttal workflows, not only first-pass reviewing.

### Manuscripts are untrusted input

Prompt-like text inside a manuscript is data, not runtime instruction. Submitted research code is inspected but not executed by default.

## Inputs

Referee can inspect combinations of:

- PDF, DOCX, Markdown, plain text, LaTeX, JATS/XML, HTML;
- supplementary files;
- spreadsheets and CSV files;
- notebooks and common source-code files;
- bibliography/reference files;
- reviewer comments, rebuttals, and prior manuscript versions for supported review modes.

DOCX inspection includes OOXML/OMML structure, comments, tracked changes, tables, media, external relationships, and plaintext-math signals.

## Review depth and purpose

Depth and purpose are separate controls.

| Depth | Intended use |
|---|---|
| `standard` | Fast bounded review; up to one targeted specialist |
| `deep` | Recommended default; up to three targeted specialists |
| `exhaustive` | Broader specialist coverage plus a fresh reassessment of top verified concerns |

Supported review purposes include `initial`, `revision`, `rebuttal`, `meta_review`, `editorial_screen`, and `reproducibility`.

Named configuration profiles are available for balanced review, editorial screening, full audit, reproducibility, and revision closure:

```bash
referee list-profiles
referee list-modes
```

## Useful commands

Inspect a manuscript/reproducibility package without any model call:

```bash
referee inspect-package manuscript.docx supplement.docx data.xlsx analysis.ipynb
```

Compare revisions:

```bash
referee compare-revision original.docx revised.docx --json-out revision_diff.json
```

Audit a response letter:

```bash
referee audit-rebuttal response_to_reviewers.docx
```

Add an evidence-bound diagnostic scorecard after the scientific state is frozen:

```bash
referee review manuscript.pdf --mode deep --scorecard --model "$REFEREE_MODEL"
```

Freeze and verify a completed handoff:

```bash
referee finalize-run runs/<run-id>
referee verify-handoff runs/<run-id>/artifacts/referee-handoff.zip
```

Start the optional local workbench:

```bash
python -m pip install -e '.[server]'
referee serve --run-root runs --port 8765
```


## Outputs

A completed run may contain:

- `review.md`, `review.json`, and `review.html`;
- `core_peer_review.json` and deterministic validation records;
- `major_concerns.csv`;
- document/package/reporting/reproducibility audits;
- concern-admission and independent-verification records;
- evidence/provenance graphs and reports;
- stage checkpoints and `events.jsonl`;
- `run_manifest.json` with input/final-state hashes;
- optional human workspace notes/statuses kept separate from model scientific state;
- finalization quality snapshots, closure matrices, and checksum-verifiable handoff bundles.

## Scholarly search providers

Built-in adapters include Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv, and Europe PMC. List the providers available in your installation with:

```bash
referee list-scholarly-providers
```

Provider implementations are replaceable. Scientific concern admission, provenance, and closure rules remain inside Referee rather than inside any single provider prompt.

## Validation and reproducibility

Referee deliberately separates **software/integrity validation** from **scientific-review validity**.

Run the complete offline release validation:

```bash
python scripts/rebuild_package_metadata.py
python scripts/validate_package.py
```

Or run the one-command deterministic validation campaign:

```bash
referee validate --suite integrity --output validation-results
```

The repository currently includes:

- 1,057 structured synthetic validation cases;
- hidden structured gold for positive scientific/domain cases;
- counterfactual defect→repair and predeclared ablation tooling;
- 43 deterministic provenance/security/contract adversarial checks;
- binary DOCX/PDF/notebook/LaTeX regression fixtures;
- a frozen validation-release manifest and SHA-256 package manifest.

Passing these checks establishes that the implementation follows its declared contracts. It **does not** establish equivalence to expert peer reviewers, superiority to other systems, or calibrated journal acceptance prediction. The project intentionally does not make those claims without corresponding empirical evidence.

For details, see [`docs/evaluation/VALIDATION.md`](docs/evaluation/VALIDATION.md) and [`benchmark_corpus/README.md`](benchmark_corpus/README.md).

## Benchmarks

A hidden-gold development benchmark can be run with:

```bash
python scripts/run_benchmark_suite.py --model "$REFEREE_MODEL" --limit-per-corpus 10 --repeats 3
```

Counterfactual and ablation runners are separate:

```bash
python scripts/run_mutation_benchmark.py --model "$REFEREE_MODEL"
python scripts/run_ablation_benchmark.py --model "$REFEREE_MODEL"
```

Synthetic benchmark content must never be used as scientific evidence in a manuscript review.

## Portable prompts

[`dist/BEIHANG_REFEREE_PROMPT.md`](dist/BEIHANG_REFEREE_PROMPT.md) is a portable prompt build for environments that cannot run the Python package. [`dist/BEIHANG_REFEREE_FULL_AUDIT_PROMPT.md`](dist/BEIHANG_REFEREE_FULL_AUDIT_PROMPT.md) provides the broader full-audit prompt.

Portable prompts preserve model-facing review instructions but **cannot** reproduce runtime guarantees such as hash-bound provenance, deterministic routing, citation/source opening, hard concern admission, deduplication, or frozen handoff integrity. Use the Python runtime when those guarantees matter.

## Repository map

| Path | Purpose |
|---|---|
| `referee/` | Executable Python runtime |
| `core/` | Scientific contracts and core prompts |
| `agents/`, `skills/` | Specialist review assets |
| `profiles/`, `config/` | Domain, reporting, benchmark, journal, and runtime profiles |
| `schemas/` | Machine-checkable contracts |
| `benchmark_corpus/`, `evals/` | Validation corpora and evaluation support |
| `fixtures/`, `tests/` | Regression artifacts and source tests |
| `docs/` | Architecture, evaluation, and operator documentation |
| `examples/` | Deterministic offline demo |
| `frontend/`, `referee/server/` | Optional local review workbench |
| `dist/` | Portable prompt builds |

Start with [`docs/README.md`](docs/README.md) for a documentation index.

## Security, confidentiality, and responsible use

Formal confidential peer review may be subject to journal/publisher rules restricting AI assistance or external processing. Referee never assumes such use is permitted. Users remain responsible for confidentiality, conflicts of interest, journal policy, and scientific judgment.

Do not put credentials in manuscript directories or issue reports. Do not execute untrusted submitted code outside a properly isolated environment. See [`SECURITY.md`](SECURITY.md) for the threat model and vulnerability-reporting guidance.

## Contributing

Contributions are welcome, especially reproducible fixes for false-positive/false-negative review behavior, provider integrations, ingestion edge cases, scientific validation rules, domain packs, and documentation.

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. For help choosing the right issue type, see [`SUPPORT.md`](SUPPORT.md).

## Release integrity

Build validated distribution artifacts with:

```bash
make release
```

The distribution builder regenerates package metadata, runs the repository validation gate, builds the source ZIP and wheel, and writes SHA-256 hashes for the generated artifacts.

## Project boundaries

Beihang Referee is decision-support software. It does not autonomously decide whether work should be published, and its output should not be treated as authoritative peer review. Human reviewers, authors, editors, and users remain responsible for interpreting and independently checking the scientific output.

## License

Beihang Referee is distributed under the MIT License. See [`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
