from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Category-level hidden scientific mechanism templates. These are not shown to
# Referee during manuscript review. They are used only after a run has finished.
CONCEPTS: dict[str, list[list[str]]] = {
    "causal_without_identification": [["observational", "single-time-point", "nonrandomized"], ["causes", "causal"], ["no identification", "no confounder adjustment", "confounding"]],
    "data_leakage": [["feature selection before cross-validation", "feature selection using full dataset", "screening before folds"], ["held-out", "test-fold", "validation-fold"], ["influence model construction", "information leakage", "leaks into training", "held-out folds influence feature selection", "test-fold information affects predictors"]],
    "optimistic_validation": [["tuned and evaluated on the same validation set", "same validation set", "validation reused for tuning"], ["external validation", "test performance described as external"], ["optimistic", "not independent"]],
    "denominator_mismatch": [["184", "176", "171"], ["participant", "denominator", "attrition"], ["without explanation", "unexplained"]],
    "effect_ci_inconsistency": [["0.42", "point estimate"], ["0.51", "0.73", "confidence interval"], ["does not contain", "outside the interval"]],
    "multiple_testing": [["48 outcomes", "many outcomes", "multiple tests"], ["nominal p-values", "no multiplicity correction", "uncorrected"], ["single positive", "highlighted as confirmatory"]],
    "baseline_obsolescence": [["state-of-the-art", "sota"], ["old baseline", "several generations earlier", "weak baseline"], ["stronger recent baselines", "recent comparator"]],
    "novelty_overclaim": [["first approach", "novelty claim"], ["one keyword", "limited search"], ["nearest prior art", "prior-art analysis"]],
    "unit_inconsistency": [["mg/l", "mg L"], ["µg/ml", "ug/ml"], ["values unchanged", "unit conversion", "numerically unchanged"]],
    "sample_pseudoreplication": [["repeated measurements", "same experimental unit"], ["independent observations", "treated as independent"], ["inflating", "nominal sample size"]],
    "posthoc_primary": [["preregistered primary", "primary endpoint"], ["not reported", "missing"], ["secondary endpoint", "presented as primary"]],
    "missing_negative_control": [["single perturbation", "perturbation experiment"], ["negative control", "control absent"], ["general stress", "alternative mechanism"]],
    "generalization_scope": [["single site", "narrow population"], ["universally", "generalise broadly", "generalize broadly"], ["external validation", "target population"]],
    "figure_text_conflict": [["figure 3", "figure"], ["negative", "positive"], ["same estimate", "direction conflict"]],
    "reporting_gap": [["randomized trial", "randomised trial"], ["allocation method", "participant flow"], ["registration identifier", "trial registration"]],
    "citation_placeholder": [["author et al., 20xx", "[ref]", "placeholder"], ["central statement", "citation"], ["unresolved", "not final reference"]],
    "area_normalization": [["projected anode area", "projected area"], ["cathode area", "total electrode area"], ["directly compared", "normalization basis", "not comparable"]],
    "polarization_protocol": [["changing external resistance", "resistance change"], ["stabilization time", "scan protocol", "steady state"], ["transient", "peak power"]],
    "coulombic_efficiency": [["coulombic efficiency", "electron recovery"], ["substrate-electron equivalent", "flow basis"], ["influent/effluent cod", "interval not aligned"]],
    "removal_vs_destruction": [["concentration decrease", "removal"], ["complete degradation", "destruction", "mineralization"], ["mass balance", "toxicity", "products"]],
    "loading_context": [["removal percentages", "percentage removal"], ["different influent concentrations", "different loading"], ["hydraulic retention time", "hrt"]],
    "single_micrograph": [["one selected sem", "single micrograph"], ["replicate fields", "quantitative morphology"], ["structure–performance", "mechanism"]],
    "peak_assignment": [["spectroscopy peak", "peak assignment"], ["specific functional group", "chemical assignment"], ["reference spectra", "fit uncertainty", "alternative assignments"]],
    "abundance_activity": [["relative abundance", "taxon abundance"], ["direct evidence", "drives current", "activity"], ["metabolic activity", "causal electroactivity"]],
    "compositional_stats": [["relative-abundance", "compositional"], ["ordinary correlations", "correlation"], ["multiple testing", "compositional constraints"]],
    "gross_net": [["gross electrical output", "gross energy"], ["net-positive", "net energy"], ["pumping", "mixing", "aeration", "auxiliary loads"]],
    "functional_unit": [["functional unit", "system boundary"], ["different", "incompatible"], ["life-cycle", "lca", "environmental advantage"]],
    "mesh_independence": [["single mesh", "one mesh"], ["time step", "convergence"], ["mesh-independence", "numerical solution error"]],
    "below_resolution": [["instrument resolution", "resolution"], ["differ by less", "below resolution"], ["physically meaningful", "claimed effect"]],
    "feature_importance_mechanism": [["shap", "feature importance"], ["proving", "mechanism", "chemical mechanism"], ["predictive attribution", "causal explanation"]],
    "group_leakage": [["same reactor", "same specimen", "same group"], ["training and test", "both folds"], ["not independent", "optimistic performance"]],
    "linear_extrapolation": [["bench-scale", "pilot scale"], ["linearly extrapolated", "linear extrapolation"], ["geometry", "transport", "pressure drop", "auxiliary loads"]],
    "r2_calibration": [["r²=0.999", "r2=0.999", "high r2"], ["residual analysis", "recovery", "range validation", "uncertainty"], ["calibration", "quantitative"]],
    "verification_validation": [["experimental curve", "validation"], ["numerical verification", "solver verification"], ["analytic", "benchmark verification", "conflated"]],
}


CONSEQUENCES: dict[str, str] = {
    "causal_without_identification": "Because the design does not identify a causal effect, the manuscript's central causal conclusion is unsupported; the observed association may reflect confounding or selection rather than the claimed causal mechanism.",
    "data_leakage": "Because held-out observations influence feature selection, reported cross-validation performance may be optimistically biased and the claimed out-of-sample predictive performance is unsupported.",
    "optimistic_validation": "Reusing the same validation data for model selection and performance estimation makes the reported performance optimistically biased and unsuitable as independent generalization evidence.",
    "denominator_mismatch": "Inconsistent analysis denominators make the reported percentages and participant-level effect estimates non-reconcilable, so the affected quantitative conclusion cannot be verified.",
    "effect_ci_inconsistency": "A reported point estimate lying outside its stated confidence interval is internally impossible under the claimed summary, so the affected effect estimate or interval is erroneous.",
    "multiple_testing": "Without multiplicity control or a prespecified confirmatory endpoint, the highlighted nominally significant result does not control the stated false-positive risk and cannot support a confirmatory claim.",
    "baseline_obsolescence": "Comparison only with obsolete or materially weaker baselines does not substantiate the claimed state-of-the-art performance against current alternatives.",
    "novelty_overclaim": "The manuscript's novelty claim is not established because the prior-art search is too limited to rule out substantially overlapping earlier work.",
    "unit_inconsistency": "The unchanged numerical values under incompatible units create a dimensional inconsistency, so the affected concentration or derived quantitative result is unreliable until corrected.",
    "sample_pseudoreplication": "Treating repeated observations from the same experimental unit as independent can underestimate uncertainty and inflate significance for the affected comparison.",
    "posthoc_primary": "Presenting a secondary or post-hoc endpoint as the primary outcome changes the inferential status of the result and can overstate confirmatory evidence.",
    "missing_negative_control": "Without an appropriate negative control, the observed response cannot distinguish the proposed mechanism from nonspecific perturbation or general stress.",
    "generalization_scope": "Evidence from a single site or narrow population does not support the manuscript's broad population-level generalization without external validation or a narrowed claim.",
    "reporting_gap": "Missing allocation, flow, or registration information prevents verification of key trial-design safeguards and limits reproducibility, but does not by itself prove the procedure was invalid.",
    "figure_text_conflict": "Opposite effect directions in the figure and text make the affected scientific result internally inconsistent; at least one representation is wrong or mislabeled.",
    "citation_placeholder": "An unresolved placeholder cannot substantiate the central externally supported statement, leaving that claim without a verifiable source.",
}

RESOLUTIONS: dict[str, list[str]] = {
    "data_leakage": ["perform feature selection independently inside every training fold", "nest feature selection within cross-validation"],
    "sample_pseudoreplication": ["reanalyze using the experimental unit", "model within-unit dependence"],
    "multiple_testing": ["apply multiplicity control", "reframe as exploratory with appropriate uncertainty"],
    "causal_without_identification": ["remove unsupported causal language", "provide a valid identification strategy"],
    "unit_inconsistency": ["convert all quantities to a common unit", "correct the inconsistent unit/value"],
    "denominator_mismatch": ["reconcile denominators and analysis populations", "document participant flow and use one traceable denominator for each estimate"],
    "optimistic_validation": ["separate model selection from final performance evaluation", "evaluate the finalized model on an untouched test set or nested validation procedure"],
    "effect_ci_inconsistency": ["recompute the point estimate and confidence interval from the same analysis", "correct the inconsistent estimate or interval everywhere it appears"],
    "baseline_obsolescence": ["compare against current technically appropriate baselines", "narrow the state-of-the-art claim if current baselines cannot be evaluated"],
    "novelty_overclaim": ["perform and document a broader prior-art search", "narrow the novelty claim to what verified prior art supports"],
    "posthoc_primary": ["restore the preregistered primary endpoint as confirmatory", "label the post-hoc endpoint exploratory and narrow claims accordingly"],
    "missing_negative_control": ["add or analyze an appropriate negative control", "narrow the mechanistic interpretation to what the existing design can support"],
    "generalization_scope": ["narrow the population/generalization claim", "provide independent external validation in the target population"],
    "reporting_gap": ["report the missing allocation, flow, and registration information needed to verify the design"],
    "figure_text_conflict": ["reconcile the figure and text to the same verified estimate and direction"],
    "citation_placeholder": ["replace the placeholder with a verified source that supports the stated proposition", "remove or narrow the unsupported statement"],
}

FORBIDDEN: dict[str, list[str]] = {
    "data_leakage": ["insufficient sample size", "lack of external validation alone"],
    "sample_pseudoreplication": ["sample size too small"],
    "causal_without_identification": ["needs a larger sample only"],
}


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def structured_gold_for_case(case: dict[str, Any]) -> dict[str, Any] | None:
    gold = case.get("gold_concern") or case.get("gold")
    if not isinstance(gold, dict):
        return None
    category = str(case.get("category") or "unknown")
    groups = CONCEPTS.get(category)
    if not groups:
        # Fail closed rather than pretending an unstructured defect is valid.
        return None
    return {
        "defect_id": category.upper(),
        "case_id": case.get("case_id"),
        "category": category,
        "severity": gold.get("severity") or case.get("expected_severity") or "major",
        "affected_claim_types": [gold.get("claim_type") or case.get("claim_type")] if (gold.get("claim_type") or case.get("claim_type")) else [],
        "required_mechanism_concepts": [{"concept": g[0], "acceptable_phrases": g} for g in groups],
        "scientific_consequence": [CONSEQUENCES.get(category, str(gold.get("scientific_consequence") or ""))],
        "acceptable_resolutions": RESOLUTIONS.get(category, [str(gold.get("minimum_resolution") or gold.get("closure_criterion") or "scientifically resolve the stated failure mechanism")]),
        "forbidden_misdiagnoses": FORBIDDEN.get(category, []),
        "gold_failure_mechanism": str(gold.get("failure_mechanism") or ""),
        "gold_scientific_consequence": CONSEQUENCES.get(category, str(gold.get("scientific_consequence") or "")),
        "gold_minimum_resolution": (RESOLUTIONS.get(category) or [str(gold.get("minimum_resolution") or "")])[0],
        "gold_closure_criterion": ("The concern is resolved when " + (RESOLUTIONS.get(category) or [str(gold.get("closure_criterion") or "the stated mechanism is corrected")])[0] + " and the affected claim is re-evaluated without contradictory reporting."),
    }


def build_structured_gold(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    out: list[dict[str, Any]] = []
    for name in ("scientific_defect_cases.jsonl", "domain_science_cases.jsonl"):
        for line in (root / name).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            sg = structured_gold_for_case(case)
            if sg:
                out.append(sg)
    return out


def load_structured_gold(root: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(root) / "structured_gold.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {str(r["case_id"]): r for r in rows}
