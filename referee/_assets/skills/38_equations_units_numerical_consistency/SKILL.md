# Skill: Equations, Units & Numerical Consistency

## Purpose

Detect mathematical, unit, denominator, and cross-document inconsistencies that can silently invalidate interpretation.

## Procedure

Build a numerical fact ledger for central results. Check equation definitions, symbol reuse, algebraic consistency where tractable, dimensional consistency, units, conversions, percentages, denominators, sample sizes, confidence/credible intervals, p-values, totals/subtotals, benchmark scores, and values repeated across abstract, main text, figures, tables, supplement, and code outputs. Recalculate simple derived quantities when feasible and label `[CALC]`. For complex derivations, identify the exact unverified step rather than pretending full proof verification.

## Required outputs

Numerical fact ledger; equation/unit issue table; cross-file discrepancy log; corrected derived values where safely calculable.

## Guardrails / failure modes

Do not infer fraud from inconsistency. Distinguish typographical, reporting, computational, and interpretation-level discrepancies. Never invent missing raw values.
