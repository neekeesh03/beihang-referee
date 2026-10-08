# Skill: Machine Learning for Scientific Inference

## Purpose

Audit ML workflows used to support scientific, materials, chemical, biological, or engineering claims.

## Procedure

Check split unit, leakage through preprocessing/feature selection, nested tuning, baseline strength, temporal/group/site separation, label quality, class imbalance, calibration, uncertainty, ablations, representation leakage, hyperparameter search budget, repeated seeds, external validation, and interpretability claims. For scientific inference, distinguish predictive association from mechanistic explanation.

## Required outputs

Data-split diagram; leakage audit; baseline matrix; validation/calibration audit; ablation/repeatability gaps; inference-scope limits.

## Guardrails / failure modes

Do not treat feature importance as mechanism. Do not allow test-set reuse for model selection. Require entity/group-aware splits when multiple measurements derive from one specimen/reactor/patient.
