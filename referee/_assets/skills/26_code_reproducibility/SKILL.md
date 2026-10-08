# Skill: Code, Data & Reproducibility

## Purpose

Determine whether computational results can be reproduced and whether implementation matches the scientific description.

## Procedure

Static inspect first. Check README, environment/lockfiles, package versions, seeds, preprocessing, file paths, data availability, executable entry points, tests, figure scripts, hard-coded outputs, undocumented manual steps, commit/version consistency and license/access limitations. Execute only in a secure sandbox if explicitly allowed.

## Required outputs

Reproducibility checklist; code-paper mismatches; execution risk; minimum steps for reproduction.

## Guardrails / failure modes

Never run untrusted code with network/secrets. Do not execute destructive scripts.
