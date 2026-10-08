from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
from typing import Any
import re

# Canonical PUBLIC major-concern contract. This mirrors the core peer-review
# prompt. Runtime provenance/generator metadata is stored outside this model so
# it can never be mistaken for scientific content authored by the reviewer.

@dataclass(slots=True)
class Concern:
    concern_id: str
    title: str
    severity: str
    claim_ids: list[str]
    evidence_anchor_ids: list[str]
    failure_mechanism: str
    scientific_consequence: str
    minimum_resolution: str
    closure_criterion: str
    reviewer_confidence: float
    steelman: str
    steelman_survives: bool
    steelman_survival_reason: str
    external_verification_required: bool = False
    uncertainties: list[str] = field(default_factory=list)
    suggested_validation_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> "Concern":
        d = normalize_concern(obj)
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in allowed})

    def scientific_payload(self) -> dict[str, Any]:
        """Stable scientific fields whose mutation invalidates verification."""
        return self.to_dict()


def _confidence_to_float(value: Any) -> Any:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    mapping = {
        "high": 0.90,
        "moderate": 0.70,
        "medium": 0.70,
        "low": 0.40,
        "unassessable": 0.0,
        "uncertain": 0.40,
    }
    if isinstance(value, str):
        return mapping.get(value.strip().lower(), value)
    return value


def normalize_concern(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize full field names without manufacturing required science.

    Backward aliases are accepted for imported historical artifacts, but fields
    that the core prompt requires (steelman, survival reason, etc.) are never
    invented here. Their absence must fail deterministic validation.
    """
    d = dict(obj or {})
    if "evidence_anchor_ids" not in d and "evidence_anchors" in d:
        value = d.pop("evidence_anchors")
        if isinstance(value, list):
            value = [x.get("anchor_id") if isinstance(x, dict) else x for x in value]
        d["evidence_anchor_ids"] = value
    if "failure_mechanism" not in d and d.get("mechanism"):
        d["failure_mechanism"] = d.pop("mechanism")
    if "reviewer_confidence" not in d and "confidence" in d:
        d["reviewer_confidence"] = _confidence_to_float(d.pop("confidence"))
    elif "reviewer_confidence" in d:
        d["reviewer_confidence"] = _confidence_to_float(d["reviewer_confidence"])
    if "steelman_survives" not in d and "steelman_survival" in d:
        d["steelman_survives"] = d.pop("steelman_survival")
    if "failure_mechanism" not in d and d.get("issue"):
        d["failure_mechanism"] = d["issue"]
    # Old severity labels are normalized only to the public three-level scheme.
    if d.get("severity") == "critical":
        d["severity"] = "major"
    if d.get("severity") == "note":
        d["severity"] = "observation"
    d.setdefault("external_verification_required", False)
    d.setdefault("uncertainties", [])
    d.setdefault("suggested_validation_checks", [])
    return d


def concern_json_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "major_comment.schema.json",
        "title": "RefereeMajorConcern",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "concern_id", "title", "severity", "claim_ids", "evidence_anchor_ids",
            "failure_mechanism", "scientific_consequence", "minimum_resolution",
            "closure_criterion", "reviewer_confidence", "steelman",
            "steelman_survives", "steelman_survival_reason",
            "external_verification_required", "uncertainties", "suggested_validation_checks",
        ],
        "properties": {
            "concern_id": {"type": "string", "pattern": "^MC(?:[0-9]{3,}|-[A-Z0-9-]+-[0-9]{4})$"},
            "title": {"type": "string", "minLength": 3},
            "severity": {"const": "major"},
            "claim_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "pattern": "^C(?:[0-9]{3,}|-[A-Z0-9-]+-[0-9]{4})$"}},
            "evidence_anchor_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "pattern": "^A(?:[0-9]{3,}|-[A-Z0-9-]+-[0-9]{4})$"}},
            "failure_mechanism": {"type": "string", "minLength": 3},
            "scientific_consequence": {"type": "string", "minLength": 3},
            "minimum_resolution": {"type": "string", "minLength": 3},
            "closure_criterion": {"type": "string", "minLength": 3},
            "reviewer_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "steelman": {"type": "string", "minLength": 3},
            "steelman_survives": {"type": "boolean"},
            "steelman_survival_reason": {"type": "string", "minLength": 3},
            "external_verification_required": {"type": "boolean"},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
            "suggested_validation_checks": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_concern_contract(
    obj: dict[str, Any],
    *,
    known_claim_ids: set[str] | None = None,
    known_anchor_ids: set[str] | None = None,
) -> list[str]:
    d = normalize_concern(obj)
    errors: list[str] = []
    required = set(concern_json_schema()["required"])
    missing = sorted(required - set(d))
    if missing:
        errors.append(f"missing fields: {missing}")
    if d.get("severity") != "major":
        errors.append("severity must be exactly 'major'")
    cid = str(d.get("concern_id") or "")
    if not re.fullmatch(r"MC(?:\d{3,}|-[A-Z0-9-]+-\d{4})", cid):
        errors.append("concern_id must be a local MC### or runtime canonical MC-<SOURCE>-#### ID")
    claims = [str(x) for x in (d.get("claim_ids") or []) if str(x)]
    anchors = [str(x) for x in (d.get("evidence_anchor_ids") or []) if str(x)]
    if not claims:
        errors.append("claim_ids empty")
    if not anchors:
        errors.append("evidence_anchor_ids empty")
    if len(set(claims)) != len(claims):
        errors.append("duplicate claim_ids")
    if len(set(anchors)) != len(anchors):
        errors.append("duplicate evidence_anchor_ids")
    if known_claim_ids is not None:
        unknown = sorted(set(claims) - known_claim_ids)
        if unknown:
            errors.append(f"unknown claims: {unknown}")
    if known_anchor_ids is not None:
        unknown = sorted(set(anchors) - known_anchor_ids)
        if unknown:
            errors.append(f"unknown anchors: {unknown}")
    for key in (
        "title", "failure_mechanism", "scientific_consequence", "minimum_resolution",
        "closure_criterion", "steelman", "steelman_survival_reason",
    ):
        if not str(d.get(key, "")).strip():
            errors.append(f"{key} empty")
    conf = d.get("reviewer_confidence")
    if not isinstance(conf, (int, float)) or isinstance(conf, bool) or not (0.0 <= float(conf) <= 1.0):
        errors.append("reviewer_confidence must be numeric in [0,1]")
    elif float(conf) < 0.50:
        errors.append("reviewer_confidence below 0.50 cannot be admitted as a major concern")
    if d.get("steelman_survives") is not True:
        errors.append("steelman_survives must be true for a major concern")
    if d.get("external_verification_required") is True:
        errors.append("major concern still requires external verification")
    if not isinstance(d.get("uncertainties", []), list):
        errors.append("uncertainties must be an array")
    if not isinstance(d.get("suggested_validation_checks", []), list):
        errors.append("suggested_validation_checks must be an array")
    return errors
