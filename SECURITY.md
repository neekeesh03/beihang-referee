# Security and confidentiality

Beihang Referee treats every manuscript, supplement, reviewer comment, archive, spreadsheet, notebook, bibliography, and code attachment as **untrusted input**.

## Threat model

The project is designed around several practical risks:

- prompt injection embedded in manuscript text or metadata;
- malicious or surprising document/container structure;
- unsafe submitted code or notebooks;
- path traversal and unsafe file references;
- external relationships or links in Office documents;
- credential leakage into prompts, logs, issues, or artifacts;
- untrusted external scholarly content;
- confidential manuscripts being sent to a provider without authorization.

Prompt-like manuscript text is data and must not become runtime instruction. Submitted research code is inspected but is not executed by default.

## Credentials

Keep model/search credentials outside manuscript-accessible paths. Use environment variables or a suitable secret manager. Never commit `.env`, API keys, private keys, access tokens, or credentials to the repository.

The included `.env.example` contains variable names only.

## Confidential review

Formal peer review can be confidential and may be subject to journal, publisher, employer, funder, or institutional restrictions on AI tools and external processing. Referee does not assume permission. Before processing confidential material, users must verify that the intended provider, network path, storage behavior, and AI-assisted workflow are allowed.

When confidentiality is material, consider disabling external scholarly retrieval and using appropriately controlled model infrastructure.

## Untrusted research code

Do not enable execution of submitted code in an unsandboxed environment. Inspection and reproducibility metadata are not a reason to trust a notebook, script, macro, binary, or archive.

If future integrations add execution, they should use an isolated disposable environment with restricted filesystem access, credentials, privileges, and network egress.

## Reporting a vulnerability

Do not publish exploit details, credentials, confidential manuscripts, or private data in a normal GitHub issue.

If private vulnerability reporting is enabled in the repository's **Security** tab, use that channel. Otherwise, contact a maintainer through a private GitHub channel before disclosing technical exploit details publicly.

A useful vulnerability report includes the affected version, minimal reproduction, security impact, required preconditions, and whether the issue can expose credentials, files, network access, or confidential content.

## Security telemetry vs. scientific evidence

Prompt-injection strings, external relationships, suspicious paths, secret-like values, and other security signals should be treated as security telemetry. They are not automatically scientific defects in the manuscript and must not be converted into scientific criticism without an independent scientific basis.
