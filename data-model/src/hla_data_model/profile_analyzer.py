"""Build an explainable patient-profile restitution without medical scoring."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable


PROFILE_CONTEXT_FIELDS = (
    "sex_at_birth",
    "dialysis",
    "rejection_suspicion",
    "organ_context",
)
UNAVAILABLE_STATES = {"missing", "contradictory"}


class ProfileAnalysisError(ValueError):
    """Raised when the patient profile cannot satisfy the source contract."""


@dataclass(frozen=True)
class FactorDefinition:
    factor_id: str
    source_field: str
    label: str
    rule_status: str
    justification: str
    value_reader: Callable[[dict[str, Any]], Any]


def _scalar(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda profile: profile[name].get("value")


def _count(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda profile: profile[name].get("count")


def _events(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda profile: deepcopy(profile[name].get("events", []))


FACTOR_DEFINITIONS = (
    FactorDefinition("PF-01", "age", "Age", "pending_review", "Age rule awaits Ahmed's validation.", _scalar("age")),
    FactorDefinition(
        "PF-02",
        "pregnancy_history",
        "Pregnancy history",
        "pending_review",
        "Pregnancy rule awaits Ahmed's validation.",
        _count("pregnancy_history"),
    ),
    FactorDefinition(
        "PF-03", "diabetes", "Diabetes", "blocked", "Diabetes contribution is undefined.", _scalar("diabetes")
    ),
    FactorDefinition(
        "PF-04",
        "hypertension",
        "Hypertension",
        "blocked",
        "Hypertension contribution is undefined.",
        _scalar("hypertension"),
    ),
    FactorDefinition(
        "PF-05",
        "autoimmune_disease",
        "Autoimmune disease",
        "blocked",
        "Autoimmune disease contribution is undefined.",
        _scalar("autoimmune_disease"),
    ),
    FactorDefinition(
        "PF-06",
        "previous_transplants",
        "Previous transplant",
        "blocked",
        "Previous transplant contribution is undefined.",
        _events("previous_transplants"),
    ),
    FactorDefinition(
        "PF-07",
        "transfusion_history",
        "Transfusion history",
        "pending_review",
        "Transfusion rule awaits Ahmed's validation.",
        lambda profile: {
            "count": profile["transfusion_history"].get("count"),
            "frequency": profile["transfusion_history"].get("frequency"),
        },
    ),
    FactorDefinition(
        "PF-08",
        "car_t_treatments",
        "CAR-T treatment",
        "blocked",
        "CAR-T contribution is undefined.",
        _events("car_t_treatments"),
    ),
    FactorDefinition(
        "PF-09",
        "therapeutic_antibody_treatments",
        "Therapeutic antibody treatment",
        "blocked",
        "Other antibody-based treatment contribution is undefined.",
        _events("therapeutic_antibody_treatments"),
    ),
)


def _missing_reason(source_field: str, label: str, availability: str) -> str:
    if source_field == "age" and availability == "missing":
        return "Age is absent from the source record."
    if source_field == "hypertension" and availability == "contradictory":
        return "Two source observations contradict each other."
    if availability == "missing":
        return f"{label} is absent from the source record."
    return f"Source observations for {label.lower()} contradict each other."


def _factor_justification(definition: FactorDefinition, availability: str) -> str:
    if definition.source_field == "age" and availability == "missing":
        return "Age is missing and must not be interpreted as zero."
    if definition.source_field == "hypertension" and availability == "contradictory":
        return "Contradictory hypertension observations require human resolution."
    if availability == "missing":
        return f"{definition.label} is missing and cannot contribute a favorable value."
    if availability == "contradictory":
        return f"Contradictory {definition.label.lower()} observations require human resolution."
    return definition.justification


def _require_profile_fields(patient_profile: dict[str, Any]) -> None:
    required = set(PROFILE_CONTEXT_FIELDS) | {definition.source_field for definition in FACTOR_DEFINITIONS}
    missing = sorted(required - patient_profile.keys())
    if missing:
        raise ProfileAnalysisError(f"Patient profile is missing required fields: {', '.join(missing)}")
    invalid = sorted(name for name in required if not isinstance(patient_profile[name], dict))
    if invalid:
        raise ProfileAnalysisError(f"Patient profile fields must be objects: {', '.join(invalid)}")


def analyze_profile(patient_profile: dict[str, Any]) -> dict[str, Any]:
    """Return a structured profile without computing an unvalidated score."""

    _require_profile_fields(patient_profile)
    context = {name: deepcopy(patient_profile[name]) for name in PROFILE_CONTEXT_FIELDS}
    factors: list[dict[str, Any]] = []
    missing_data: list[dict[str, str]] = []

    for definition in FACTOR_DEFINITIONS:
        observation = patient_profile[definition.source_field]
        availability = observation.get("availability")
        factors.append(
            {
                "factor_id": definition.factor_id,
                "availability": availability,
                "source_value": definition.value_reader(patient_profile),
                "contribution": None,
                "rule_status": definition.rule_status,
                "justification": _factor_justification(definition, availability),
            }
        )
        if availability in UNAVAILABLE_STATES:
            missing_data.append(
                {
                    "path": f"patient_profile.{definition.source_field}",
                    "reason": _missing_reason(definition.source_field, definition.label, availability),
                    "impact": "prevents_favorable_output",
                }
            )

    for context_name in PROFILE_CONTEXT_FIELDS:
        observation = patient_profile[context_name]
        availability = observation.get("availability")
        if availability in UNAVAILABLE_STATES:
            label = context_name.replace("_", " ").capitalize()
            missing_data.append(
                {
                    "path": f"patient_profile.{context_name}",
                    "reason": _missing_reason(context_name, label, availability),
                    "impact": "prevents_favorable_output",
                }
            )

    return {
        "profile_score": None,
        "score_status": "pending_review",
        "proposed_risk_category": "uncertain",
        "category_status": "pending_review",
        "context": context,
        "factors": factors,
        "missing_data": missing_data,
    }
