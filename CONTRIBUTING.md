# Contributing to Beihang Referee

Thank you for contributing. Referee welcomes engineering improvements, scientific-review fixes, ingestion edge cases, provider integrations, tests, documentation, domain packs, and reproducible reports of review-quality failures.

The project has one non-negotiable design principle: **model confidence is not evidence**. Changes that affect scientific judgments must preserve traceability, fail-closed admission, and testable closure.

## Before you start

Please do not include confidential manuscripts, unpublished reviewer reports, credentials, personal data, or publisher-restricted content in issues, tests, fixtures, or pull requests. Reduce a problem to a synthetic or public example whenever possible.

For security vulnerabilities, follow [`SECURITY.md`](SECURITY.md) rather than opening a public exploit report.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev,office,pdf,validation]'
```

Run the public offline demo:

```bash
referee review examples/demo_manuscript.md \
  --pipeline core \
  --mode standard \
  --provider scripted \
  --scripted-responses examples/demo_responses.json \
  --search-backend none \
  --run-id contributor-demo
```

## Validation before a pull request

At minimum, run:

```bash
pytest -q
python scripts/rebuild_package_metadata.py
python scripts/validate_package.py
```

`validate_package.py` is the release gate. It checks synchronized runtime assets, schemas, source compilation, tests, deterministic evidence-lock evals, benchmark readiness, frozen validation identity, adversarial integrity checks, and the offline validation campaign.

If your change modifies source assets under `core/`, `agents/`, `skills/`, `guidelines/`, `profiles/`, `config/`, `schemas/`, `validation/`, `frontend/`, or `benchmark_corpus/`, regenerate synchronized package assets with:

```bash
python scripts/rebuild_package_metadata.py
```

Do not manually edit `checksums.sha256` or `MANIFEST.json`.

## What a good contribution includes

### Runtime or scientific-kernel changes

Include a regression test that demonstrates the failure mode before the fix and passes afterward. If the behavior concerns major-comment admission, citation support, provenance, closure, routing, or verification, prefer a deterministic unit/regression case in addition to any model-backed example.

New major-comment rules must remain machine-testable. A rule should identify what evidence is required, what causes it to fail, and whether failure should reject, downgrade, or defer the concern.

### Review-quality reports

For a false positive or false negative, include only non-confidential information and, when possible:

- Referee version and commit;
- pipeline, mode, profile, provider, and model family;
- whether scholarly search was enabled;
- the smallest synthetic/public manuscript excerpt that reproduces the behavior;
- the admitted/rejected concern record and relevant evidence anchors;
- what you believe the correct scientific outcome should be and why.

Do **not** submit hidden model chain-of-thought or confidential manuscript text.

### Providers and integrations

New model/search providers should preserve source provenance, expose failures clearly, obey configured timeouts/retries, and degrade gracefully when external services are unavailable. Provider logic must not bypass Referee's evidence/admission/closure rules.

See [`docs/guides/PROVIDER_DEVELOPMENT.md`](docs/guides/PROVIDER_DEVELOPMENT.md).

### New domain packs or scientific skills

Keep the scope narrow and explicit. Domain-specific guidance should distinguish hard validity requirements from preferences or conventions. If a new rule can create a major criticism, add a regression or benchmark case showing when it should and should not fire.

### Reporting-guideline support

Do not encode a stale checklist as permanent truth. Profiles should make clear when current authoritative reporting guidance must be consulted for formal compliance.

### Documentation

Prefer commands that are executable as written. If you add a public example, make it deterministic where practical and add a regression test so it does not silently become stale.

## Pull-request expectations

A pull request should explain:

1. the failure mode or user problem;
2. the smallest change that resolves it;
3. the tests or validation proving the change;
4. any compatibility, security, scientific, or cost implications.

Keep unrelated refactors out of focused fixes. Avoid changing scientific contracts and public APIs in the same pull request unless the coupling is necessary and documented.

## Release discipline

Keep public-facing names stable and avoid embedding internal iteration history in user-facing documentation or artifact names. Material scientific-contract changes should be documented in the relevant architecture or validation files.

## Building a release

```bash
make release
```

This regenerates metadata, executes the release validation gate, builds a source ZIP and wheel, and writes SHA-256 hashes under `release-dist/`.

## Code and design conventions

- Treat manuscript content as untrusted data.
- Do not execute submitted research code by default.
- Keep deterministic scientific controls outside provider prompts where possible.
- Prefer explicit states such as `NOT_ASSESSED`, `CONDITIONAL`, and `N/A` over manufactured confidence.
- Preserve canonical IDs and provenance when transforming scientific state.
- Never use synthetic benchmark gold as manuscript evidence.
- Keep human workspace annotations separate from model-generated scientific state.
- Avoid claims of expert equivalence or calibrated publication prediction unless supported by a frozen empirical evaluation.

## Community conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
