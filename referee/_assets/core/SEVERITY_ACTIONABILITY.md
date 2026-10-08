# Concern Severity and Admission Rules

## Major-comment admission rule

A concern may enter the final major-comment list only when it has all of the following:

1. **Anchor** — exact manuscript/code/data/external evidence location or an explicit unknown.
2. **Affected claim** — the scientific statement or inference at risk.
3. **Mechanism of concern** — why the evidence does not support the claim as written.
4. **Consequence** — what interpretation, estimate, mechanism, prediction, novelty, or generalization changes.
5. **Minimum resolution** — smallest sufficient correction, analysis, clarification, or claim narrowing.
6. **Closure criterion** — observable condition for considering the concern resolved.
7. **Reviewer confidence** — numeric value in [0,1], separated from severity; values below 0.50 normally cannot support major admission.
8. **Steelman** — the strongest reasonable interpretation favorable to the authors.
9. **Steelman survival** — the concern remains material under that interpretation, with an explicit survival reason.

If any element is missing, downgrade to a question, minor comment, search-needed item, or internal note instead of presenting it as a decisive major concern.

## Severity

Use exactly the public severity labels defined by the core prompt: **major**, **minor**, or **observation**.

Priority is separate and may be assigned only after validity is established (for example P0/P1/P2 or pairwise ranking). Do not encode priority as severity.

Do not use severity as a proxy for reviewer confidence.
