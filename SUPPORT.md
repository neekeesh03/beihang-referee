# Support

Use the repository's GitHub issue templates so problems arrive with enough information to reproduce them.

## Choose the right issue type

- **Bug report** — the software crashes, produces malformed artifacts, violates a documented invariant, or a command behaves incorrectly.
- **Review-quality report** — a concern is scientifically wrong, unsupported, incorrectly admitted/rejected, or an important issue is consistently missed.
- **Feature request** — a new workflow, format, export, domain capability, or usability improvement.
- **Provider/integration request** — support for a new model, search backend, or external interface.
- **Security issue** — do **not** use a public issue; follow [`SECURITY.md`](SECURITY.md).

## Information that helps

Include the Referee version (`referee --version`), Python version, OS, command, pipeline/mode/profile, provider/model family, and the smallest reproducible non-confidential example.

For review-quality problems, include the affected concern and evidence-anchor IDs when available. Explain the expected scientific behavior rather than only saying the result is wrong.

## Confidentiality

Never upload unpublished manuscripts, confidential reviewer reports, credentials, API keys, private datasets, or personal data merely to reproduce an issue. Replace sensitive material with a minimal synthetic example or a public source.

## Self-diagnosis

Before opening an issue, these commands often identify setup problems:

```bash
referee --version
referee inspect-package <your-files>
pytest -q
python scripts/validate_package.py
```

For installation and first-run questions, start with [`QUICKSTART.md`](QUICKSTART.md).
