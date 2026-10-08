# Validation hardening closure matrix

This file maps the final pre-benchmark peer-review requirements to executable implementation. It is a protocol/readiness record, not a scientific-performance claim.

| Requirement | Implementation | Closure evidence |
|---|---|---|
| Semantic citation proposition verification | `referee/verification/citations.py`, `LiteratureSearchStage` | Exact quotations resolve deterministically; negation/contradiction tests; paraphrases require independent entailment; decisive external evidence fails closed |
| Adversarial coverage separated by evidence type | `referee/validation/adversarial.py`, `referee/validation/behavioral.py` | Static-contract and deterministic-integrity rates are reported separately; model-backed behavioral attacks execute actual review/rebuttal workflows before the full benchmark |
| Evaluator independence classification | `referee/validation/release.py`, `referee validate` | `same_model_fresh_context`, `cross_model`, `cross_family`; internal vs independent validation labels; optional hard cross-model requirement |
| Additional-concern precision adjudication | `ScientificDefectEvaluator.evaluate_additional`, `evaluate_state_independent` | Unmatched concerns classified as valid/invalid/uncertain/duplicate; ccore-control concerns adjudicated identically; precision coverage reported |
| Multi-class severity validation | `benchmark_corpus/severity_calibration_cases.jsonl`, `evaluate_severity_state_independent` | Major/minor/observation cases; severity F1 suppressed unless all classes are represented; specific consequence/closure gold |
| Mechanism-specific hidden-gold scoring | `referee/evals/gold.py`, `referee/evals/judge.py`, `benchmark_corpus/structured_gold.jsonl` | Generic-language and wrong-mechanism cases fail; mechanism/consequence/severity/resolution are separate judgments |
| Independent Judge A/B + adjudication | `ScientificDefectEvaluator` | Fresh context/agent identities stored per judgment; evaluator identities frozen in campaign manifest |
| Global canonical IDs | `referee/validation/identifiers.py` | Collision/remapping/round-trip tests; hard uniqueness invariants |
| Scientific rebuttal closure | `RebuttalClosureStage`, rebuttal corpus, `run_full_suite` | resolution/false-closure/missed-closure/promise/regression metrics |
| Hard invariant failure | `referee/validation/invariants.py`, `referee/engine.py` | `failed_validation`, `final_review_exportable=false`, finalization refusal |
| Frozen validation protocol | `validation/VALIDATION_RELEASE.json`, `referee/validation/release.py` | live hash verification before campaign execution |
| One-command campaign | `referee validate --suite full` | installed-wheel integrity run + zero-case orchestration smoke |
| Predeclared success criteria | `validation/SUCCESS_CRITERIA.json` | frozen hash + separate primary metric reporting |
| Counterfactual sensitivity | revision pairs + `run_full_suite` | defect detection, repair recognition, causal sensitivity, persistent false concern, unrelated stability |
| Architecture ablations | `referee/evals/ablations.py` | nine predeclared configurations |
| Correctness-aware repeatability | `referee/evals/full_suite.py` | stable/unstable true and false positives reported separately |

Official model-backed benchmark scores and human expert-study outcomes are intentionally absent until those experiments are actually run. The repository freezes and validates the measurement system before results are interpreted.
