# Beihang Referee — Quickstart

This guide gets you from a fresh clone to a working review. The first path is fully offline and deterministic; the second uses an OpenAI-compatible model endpoint.

## 1. Install

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[office,pdf,validation]'
```

Confirm the CLI:

```bash
referee --version
referee list-profiles
```

## 2. Run the offline demo

No API key or network access is required.

```bash
referee review examples/demo_manuscript.md \
  --pipeline core \
  --mode standard \
  --provider scripted \
  --scripted-responses examples/demo_responses.json \
  --search-backend none \
  --run-id demo
```

Open the generated review:

```bash
cat runs/demo/artifacts/review.md
```

The checked-in reference output is [`examples/expected_demo_review.md`](examples/expected_demo_review.md).

## 3. Configure a real model

The default network provider is OpenAI-compatible.

```bash
export OPENAI_API_KEY="..."
export REFEREE_MODEL="<model-id>"
```

Optional settings:

```bash
export REFEREE_VERIFIER_MODEL="<different-model-id>"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

Never commit a real `.env` file or API key. `.env.example` contains the supported environment-variable names.

## 4. Review a manuscript

Recommended default:

```bash
referee review manuscript.pdf --mode deep --model "$REFEREE_MODEL"
```

If you do not want external scholarly retrieval:

```bash
referee review manuscript.pdf \
  --mode deep \
  --search-backend none \
  --model "$REFEREE_MODEL"
```

For a manuscript package:

```bash
referee review manuscript.docx supplement.docx data.xlsx analysis.ipynb \
  --profile full-audit \
  --model "$REFEREE_MODEL"
```

## 5. Inspect before spending model tokens

Package inspection is deterministic and does not call an LLM:

```bash
referee inspect-package manuscript.docx supplement.docx data.xlsx analysis.ipynb
```

This is useful for checking inferred file roles, hashes, OOXML/LaTeX/notebook structure, and unsupported-file warnings.

## 6. Optional post-review diagnostics

Add the evidence-bound 50-dimension scorecard only after the scientific concern set is frozen:

```bash
referee review manuscript.pdf --mode deep --scorecard --model "$REFEREE_MODEL"
```

A target-journal calibration without a frozen official-source profile is explicitly provisional:

```bash
referee review manuscript.pdf \
  --mode deep \
  --scorecard \
  --target-journal "Nature" \
  --model "$REFEREE_MODEL"
```

For evidence-grounded venue calibration, supply a journal profile built from current official journal/publisher sources:

```bash
referee review manuscript.pdf \
  --mode deep \
  --scorecard \
  --target-journal "Nature" \
  --journal-profile config/journal_profiles/my-nature-profile.json \
  --model "$REFEREE_MODEL"
```

## 7. Other workflows

```bash
# Compare manuscript versions
referee compare-revision original.docx revised.docx --json-out revision_diff.json

# Audit a reviewer-response letter
referee audit-rebuttal response_to_reviewers.docx

# List previous runs
referee list-runs

# Freeze and checksum a completed review
referee finalize-run runs/<run-id>
referee verify-handoff runs/<run-id>/artifacts/referee-handoff.zip
```

## 8. Run the release-quality validation gate

```bash
python scripts/rebuild_package_metadata.py
python scripts/validate_package.py
```

For the deterministic campaign interface:

```bash
referee validate --suite integrity --output validation-results
```

## Next reading

- [`README.md`](README.md) — project overview and capabilities.
- [`docs/REVIEW_PIPELINE.md`](docs/REVIEW_PIPELINE.md) — default Core Review Pipeline architecture.
- [`docs/architecture/OVERVIEW.md`](docs/architecture/OVERVIEW.md) — runtime architecture.
- [`docs/architecture/SECURITY_MODEL.md`](docs/architecture/SECURITY_MODEL.md) — threat model.
- [`docs/guides/PROVIDER_DEVELOPMENT.md`](docs/guides/PROVIDER_DEVELOPMENT.md) — provider integration.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor workflow.
