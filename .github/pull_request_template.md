## Summary

Describe the user/scientific failure mode and the change that addresses it.

## Why this is safe

Explain any effect on concern admission, evidence/provenance, model/provider behavior, confidentiality, reproducibility, compatibility, or cost. Write `N/A` when none apply.

## Validation

- [ ] Added or updated a regression test / benchmark case where appropriate.
- [ ] `pytest -q` passes.
- [ ] `python scripts/rebuild_package_metadata.py` passes.
- [ ] `python scripts/validate_package.py` passes.
- [ ] The public offline demo still runs if this change affects the CLI/runtime contract.
- [ ] No confidential manuscript content, credentials, personal data, or generated run artifacts are included.
- [ ] New major-comment logic remains machine-testable, evidence-grounded, and closure-oriented.
- [ ] Documentation/CHANGELOG is updated if public behavior changed.

## Compatibility

List any intentional behavior/API/configuration changes. If none, write `No breaking changes`.
