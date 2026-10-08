# Review Reliability Protocol

A peer-review agent is itself a measurement system. Its output can vary across prompts, runs, models, retrieval results, and context order. Treat reviewer stability as evidence about confidence.

## Independent first pass

Where the platform permits, specialist agents should form conclusions before seeing other specialists' judgments. They may share the frozen document map, claim registry, and verified external-source ledger, but not another specialist's verdict.

## Repeated-pass check

In `exhaustive` mode, repeat at least the following on the 3–5 most consequential claims:

1. independent claim-support assessment;
2. independent red-team pass;
3. independent major-concern admission pass.

Compare the passes on:

- support status;
- decisive concern identity;
- severity;
- required resolution;
- confidence.

## Disagreement handling

Classify disagreement as:

- evidence retrieval;
- factual interpretation;
- methodological standard;
- scope/claim wording;
- novelty/search coverage;
- judgment threshold;
- residual uncertainty.

Do not average incompatible judgments. Resolve with better evidence where possible. If unresolved disagreement could change the final recommendation or a decisive gate, lower reviewer confidence and expose the disagreement.

## Stability labels

- **Stable:** independent passes agree on claim status and decisive concerns.
- **Mostly stable:** differences are wording/priority only.
- **Unstable:** support status, severity, or required resolution materially differs.
- **Unassessable:** repeatability could not be tested.

A strong-looking review with unstable decisive judgments must not be presented with high reviewer confidence.
