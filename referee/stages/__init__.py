from .core import (
    IntakeStage, PolicySecurityStage, ClassificationStage, ClaimRegistryStage,
    ReviewPlanStage, NumericalStage, LiteratureStage, SpecialistStage,
    RedTeamSteelmanStage, TrajectoryConsensusStage, ConcernProvenanceGateStage,
    ConcernVerificationStage, ConcernAdmissionStage, PriorityPairwiseStage,
    ReliabilityStage, GateAndSynthesisStage, JournalStage,
)
from .platform import PackageAuditStage, ReportingAuditStage, ReproducibilityAuditStage, DisagreementAuditStage, ProvenanceAuditStage
from .review import CORE_INITIAL_STAGES

INITIAL_STAGES = [
    IntakeStage(), PackageAuditStage(), PolicySecurityStage(), ClassificationStage(), ReportingAuditStage(), ClaimRegistryStage(),
    ReviewPlanStage(), NumericalStage(), ReproducibilityAuditStage(), LiteratureStage(), SpecialistStage(), DisagreementAuditStage(),
    RedTeamSteelmanStage(), TrajectoryConsensusStage(), ConcernProvenanceGateStage(), ConcernVerificationStage(), ConcernAdmissionStage(),
    PriorityPairwiseStage(), ProvenanceAuditStage(), ReliabilityStage(), GateAndSynthesisStage(), JournalStage(),
]

# Public full-audit stage list. ReviewEngine selects mode-specific DAGs
# through stages_for_mode() unless the caller explicitly supplies stages.
DEFAULT_STAGES = INITIAL_STAGES


def stages_for_mode(mode: str, pipeline: str = "core"):
    from .modes import (
        RevisionPreparationStage, RevisionClosureStage, RebuttalPreparationStage,
        RebuttalClosureStage, MetaReviewStage, EditorialScreenSynthesisStage,
        ReproducibilitySynthesisStage,
    )
    if pipeline == "core" and mode == "initial":
        return list(CORE_INITIAL_STAGES)
    # Non-initial workflows retain the mature full-audit DAG in Core Review Pipeline. This keeps
    # revision/rebuttal/meta-review behavior stable while the lean
    # initial-review path is benchmarked independently.
    if mode == "initial":
        return list(INITIAL_STAGES)
    if mode == "revision":
        stages = list(INITIAL_STAGES)
        stages.insert(2, RevisionPreparationStage())
        stages.insert(-2, RevisionClosureStage())
        return stages
    if mode == "rebuttal":
        stages = list(INITIAL_STAGES)
        stages.insert(2, RebuttalPreparationStage())
        stages.insert(-2, RebuttalClosureStage())
        return stages
    if mode == "meta_review":
        return [IntakeStage(), PolicySecurityStage(), MetaReviewStage()]
    if mode == "editorial_screen":
        return [IntakeStage(), PackageAuditStage(), PolicySecurityStage(), ClassificationStage(), ReportingAuditStage(), ClaimRegistryStage(), NumericalStage(), ReproducibilityAuditStage(), EditorialScreenSynthesisStage()]
    if mode == "reproducibility":
        return [IntakeStage(), PackageAuditStage(), PolicySecurityStage(), ReproducibilityAuditStage(), ReproducibilitySynthesisStage()]
    raise ValueError(f"Unsupported review mode: {mode}")

__all__ = ["DEFAULT_STAGES", "INITIAL_STAGES", "CORE_INITIAL_STAGES", "stages_for_mode"]
