# Skill: Computational Science & Numerical Verification

## Purpose

Audit numerical methods, convergence, discretization, solver choices, initialization, reproducibility, and numerical error.

## Procedure

Identify governing equations, discretization, boundary/initial conditions, solver/tolerances, mesh/time-step independence, stochastic seeds, convergence criteria, parameter estimation, and verification against analytic/benchmark cases where available. Separate model verification from validation against real data.

## Required outputs

Numerical-method ledger; convergence/mesh audit; verification-vs-validation matrix; sensitivity requirements; reproducibility risks.

## Guardrails / failure modes

Do not treat solver convergence as physical validation. Do not accept a single mesh/time step for accuracy-sensitive claims. Flag hidden default solver settings when consequential.
