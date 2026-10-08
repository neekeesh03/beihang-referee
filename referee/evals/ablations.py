from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class AblationSpec:
    name: str
    drop_stages: tuple[str, ...] = ()
    config_overrides: dict = field(default_factory=dict)
    description: str = ""

# Predeclared architecture ablations. Validity is always scored against the same
# hidden-gold evaluator; only the review architecture changes.
ABLATIONS = (
    AblationSpec("full_system", description="All Referee scientific integrity stages enabled."),
    AblationSpec("no_independent_verifier", description="Bypass independent concern verification after provenance."),
    AblationSpec("no_evidence_entailment", description="Retain structural provenance but remove entailment judgment."),
    AblationSpec("no_steelman", description="Remove the dedicated red-team/steelman stage; generator-local steelman remains schema-required."),
    AblationSpec("no_redteam", description="Remove the dedicated red-team/steelman stage; no new red-team concerns are generated."),
    AblationSpec("no_literature_search", ("07_literature",), {"enable_literature_search": False}, "Disable scholarly retrieval."),
    AblationSpec("single_specialist", (), {"specialist_limit": 1}, "Route to at most one specialist reviewer."),
    AblationSpec("no_consensus", ("09b_independent_trajectories",), {"independent_trajectories": 0}, "Disable independent-trajectory consensus."),
    AblationSpec("no_pairwise_prioritization", ("12b_priority_pairwise",), {"enable_pairwise_priority": False}, "Disable post-validity pairwise priority."),
)

def by_name(name: str) -> AblationSpec:
    for spec in ABLATIONS:
        if spec.name == name:
            return spec
    raise KeyError(name)

def apply_ablation(stages, spec: AblationSpec):
    drop = set(spec.drop_stages)
    return [s for s in stages if s.stage_id not in drop]

def build_ablation_stages(name: str, base_stages):
    """Construct the predeclared stage graph for one architecture ablation."""
    spec=by_name(name)
    stages=list(base_stages)
    if name=="no_evidence_entailment":
        from .ablation_runtime import StructuralOnlyProvenanceStage
        stages=[StructuralOnlyProvenanceStage() if s.stage_id=="10_provenance_gate" else s for s in stages]
    elif name=="no_steelman":
        from .ablation_runtime import RedTeamOnlyAblationStage
        stages=[RedTeamOnlyAblationStage() if s.stage_id=="09_redteam_steelman" else s for s in stages]
    elif name=="no_redteam":
        from .ablation_runtime import SteelmanOnlyAblationStage
        stages=[SteelmanOnlyAblationStage() if s.stage_id=="09_redteam_steelman" else s for s in stages]
    elif name=="no_independent_verifier":
        from .ablation_runtime import BypassIndependentVerifierStage, AblationAdmissionStage
        out=[]
        for s in stages:
            if s.stage_id=="11_concern_verification": out.append(BypassIndependentVerifierStage())
            elif s.stage_id=="12_concern_admission": out.append(AblationAdmissionStage())
            else: out.append(s)
        stages=out
    stages=apply_ablation(stages,spec)
    return stages,spec
