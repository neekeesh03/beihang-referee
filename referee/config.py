from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import os
from typing import Any

_MODE_DEFAULTS = {
    "standard": {
        "max_concurrency": 4,
        "max_stage_retries": 1,
        "repeatability_claims": 0,
        "specialist_limit": 6,
        "literature_query_budget": 8,
        "independent_trajectories": 0,
        "pairwise_priority_budget": 6,
    },
    "deep": {
        "max_concurrency": 6,
        "max_stage_retries": 2,
        "repeatability_claims": 2,
        "specialist_limit": 10,
        "literature_query_budget": 16,
        "independent_trajectories": 0,
        "pairwise_priority_budget": 12,
    },
    "exhaustive": {
        "max_concurrency": 8,
        "max_stage_retries": 3,
        "repeatability_claims": 5,
        "specialist_limit": 16,
        "literature_query_budget": 30,
        "independent_trajectories": 5,
        "pairwise_priority_budget": 24,
    },
}

@dataclass(slots=True)
class ReviewConfig:
    mode: str = "deep"
    pipeline: str = "core"
    review_mode: str = "initial"
    context_mode: str = "author_side_or_public_manuscript_diagnostic"
    run_root: str = "runs"
    model: str = "host-default"
    strategic_model: str | None = None
    fast_model: str | None = None
    verifier_model: str | None = None
    search_backend: str = "federated"
    document_backend: str = "local"
    max_concurrency: int | None = None
    max_stage_retries: int | None = None
    repeatability_claims: int | None = None
    specialist_limit: int | None = None
    literature_query_budget: int | None = None
    independent_trajectories: int | None = None
    pairwise_priority_budget: int | None = None
    max_major_comments: int = 12
    max_minor_comments: int = 30
    journal_candidate_target: int = 10
    allow_journal_padding: bool = False
    execute_untrusted_code: bool = False
    manuscript_network_access: bool = False
    checkpoint_each_stage: bool = True
    save_prompt_io: bool = True
    strict_schema: bool = True
    fail_closed_on_missing_anchor: bool = True
    enable_policy_gate: bool = True
    enable_literature_search: bool = True
    enable_journal_calibration: bool = True
    enable_scorecard: bool = False
    target_journal: str | None = None
    journal_profile: str | None = None
    benchmark_profile: str | None = None
    enable_reliability_pass: bool = True
    enable_package_audit: bool = True
    enable_reporting_audit: bool = True
    enable_reproducibility_audit: bool = True
    enable_disagreement_audit: bool = True
    enable_provenance_audit: bool = True
    enable_pairwise_priority: bool = True
    generate_html_report: bool = True
    generate_csv_exports: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in _MODE_DEFAULTS:
            raise ValueError(f"Unsupported mode: {self.mode}")
        if self.pipeline not in {"core", "full"}:
            raise ValueError(f"Unsupported pipeline: {self.pipeline}")
        if self.review_mode not in {"initial", "revision", "rebuttal", "meta_review", "editorial_screen", "reproducibility"}:
            raise ValueError(f"Unsupported review_mode: {self.review_mode}")
        defaults = _MODE_DEFAULTS[self.mode]
        for key, value in defaults.items():
            if getattr(self, key) is None:
                setattr(self, key, value)
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        if self.max_stage_retries < 0:
            raise ValueError("max_stage_retries must be >= 0")

    @classmethod
    def from_json(cls, path: str | Path) -> "ReviewConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)

    @classmethod
    def from_profile(cls, name: str, *, root: str | Path | None = None, **overrides: Any) -> "ReviewConfig":
        from .profiles import ProfileRegistry
        data = ProfileRegistry(root).get(name)
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)

    @classmethod
    def from_env(cls, base: "ReviewConfig | None" = None) -> "ReviewConfig":
        cfg = asdict(base or cls())
        mapping = {
            "REFEREE_MODE": ("mode", str),
            "REFEREE_PIPELINE": ("pipeline", str),
            "REFEREE_RUN_ROOT": ("run_root", str),
            "REFEREE_REVIEW_MODE": ("review_mode", str),
            "REFEREE_MODEL": ("model", str),
            "REFEREE_STRATEGIC_MODEL": ("strategic_model", str),
            "REFEREE_FAST_MODEL": ("fast_model", str),
            "REFEREE_VERIFIER_MODEL": ("verifier_model", str),
            "REFEREE_SEARCH_BACKEND": ("search_backend", str),
            "REFEREE_TARGET_JOURNAL": ("target_journal", str),
            "REFEREE_JOURNAL_PROFILE": ("journal_profile", str),
            "REFEREE_BENCHMARK_PROFILE": ("benchmark_profile", str),
            "REFEREE_MAX_CONCURRENCY": ("max_concurrency", int),
            "REFEREE_MAX_STAGE_RETRIES": ("max_stage_retries", int),
        }
        for env_name, (key, caster) in mapping.items():
            raw = os.getenv(env_name)
            if raw not in (None, ""):
                cfg[key] = caster(raw)
        return cls(**cfg)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
