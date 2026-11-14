"""Build an explainable patient-profile score from versioned synthetic inputs."""

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
OPTIONAL_PROFILE_CONTEXT_FIELDS = ("source_context",)
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
    FactorDefinition(
        "PF-01",
        "age",
        "Age",
        "validated",
        "Validated rule: age strictly above 65 contributes one point.",
        _scalar("age"),
    ),
    FactorDefinition(
        "PF-02",
        "pregnancy_history",
        "Pregnancy history",
        "validated",
        "Validated rule: zero, one, or multiple pregnancies contribute zero, one, or two points.",
        _count("pregnancy_history"),
    ),
    FactorDefinition(
        "PF-03",
        "diabetes",
        "Diabetes",
        "validated",
        "Validated rule: diabetes contributes one point when present.",
        _scalar("diabetes"),
    ),
    FactorDefinition(
        "PF-04",
        "hypertension",
        "Hypertension",
        "validated",
        "Validated rule: hypertension contributes one point when present.",
        _scalar("hypertension"),
    ),
    FactorDefinition(
        "PF-05",
        "autoimmune_disease",
        "Autoimmune disease",
        "validated",
        "Validated rule: autoimmune disease contributes two points when present.",
        _scalar("autoimmune_disease"),
    ),
    FactorDefinition(
        "PF-06",
        "previous_transplants",
        "Previous transplant",
        "validated",
        "Validated rule: each previous transplant contributes three points and a rejection history adds one point.",
        lambda profile: {
            "events": deepcopy(profile["previous_transplants"].get("events", [])),
            "rejection_history": profile["previous_transplants"].get("rejection_history", "not_applicable"),
        },
    ),
    FactorDefinition(
        "PF-07",
        "transfusion_history",
        "Transfusion history",
        "validated",
        "Validated rule: zero, one, two, or at least three transfusions contribute zero to three points.",
        lambda profile: {
            "count": profile["transfusion_history"].get("count"),
            "frequency": profile["transfusion_history"].get("frequency"),
        },
    ),
    FactorDefinition(
        "PF-08",
        "car_t_treatments",
        "Antibody-based or atypical treatment",
        "validated",
        "Validated rule: antibody-based or atypical treatment contributes one combined point when present.",
        _events("car_t_treatments"),
    ),
    FactorDefinition(
        "PF-09",
        "therapeutic_antibody_treatments",
        "Therapeutic antibody treatment",
        "validated",
        "Validated rule: antibody-based treatment shares the one-point cap with atypical treatment.",
        _events("therapeutic_antibody_treatments"),
    ),
    FactorDefinition(
        "PF-10",
        "rejection_suspicion",
        "Rejection suspicion",
        "validated",
        "Validated rule: a rejection suspicion contributes eight points.",
        _scalar("rejection_suspicion"),
    ),
    FactorDefinition(
        "PF-11",
        "initial_kidney_disease",
        "Initial kidney disease",
        "validated",
        "Validated rule: the recorded initial chronic kidney disease contributes one point.",
        _scalar("initial_kidney_disease"),
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


def _validated_contribution(
    definition: FactorDefinition,
    observation: dict[str, Any],
    source_value: Any,
    patient_profile: dict[str, Any],
) -> int | None:
    availability = observation.get("availability")
    if availability not in {"known", "not_applicable"}:
        return None
    if definition.factor_id == "PF-01":
        if not isinstance(source_value, int) or source_value < 0:
            return None
        return 1 if source_value > 65 else 0
    if definition.factor_id == "PF-02":
        if not isinstance(source_value, int) or source_value < 0:
            return None
        return 0 if source_value == 0 else 1 if source_value == 1 else 2
    if definition.factor_id == "PF-07":
        count = source_value.get("count")
        if not isinstance(count, int) or count < 0:
            return None
        return min(count, 3)
    if definition.factor_id in {"PF-03", "PF-04"}:
        return 1 if source_value is True else 0 if source_value is False else None
    if definition.factor_id == "PF-05":
        return 2 if source_value is True else 0 if source_value is False else None
    if definition.factor_id == "PF-06":
        events = source_value.get("events")
        rejection_history = source_value.get("rejection_history")
        if not isinstance(events, list):
            return None
        if not events:
            return 0
        if rejection_history not in {"yes", "no"}:
            return None
        return 3 * len(events) + (1 if rejection_history == "yes" else 0)
    if definition.factor_id == "PF-08":
        return 1 if source_value else 0 if isinstance(source_value, list) else None
    if definition.factor_id == "PF-09":
        if not isinstance(source_value, list):
            return None
        car_t_events = patient_profile["car_t_treatments"].get("events", [])
        return 0 if car_t_events else 1 if source_value else 0
    if definition.factor_id == "PF-10":
        if availability == "not_applicable":
            return 0
        return 8 if source_value is True else 0 if source_value is False else None
    if definition.factor_id == "PF-11":
        if availability == "not_applicable":
            return 0
        return 1 if isinstance(source_value, str) and source_value.strip() else None
    return None


def _risk_category(profile_score: int | None) -> tuple[str, str]:
    if profile_score is None:
        return "uncertain", "pending_review"
    if profile_score < 2:
        return "minimal", "validated"
    if profile_score < 4:
        return "moderate", "validated"
    if profile_score < 6:
        return "medium", "validated"
    if profile_score < 8:
        return "high", "validated"
    return "very_high", "validated"


def _require_profile_fields(patient_profile: dict[str, Any]) -> None:
    required = set(PROFILE_CONTEXT_FIELDS) | {definition.source_field for definition in FACTOR_DEFINITIONS}
    missing = sorted(required - patient_profile.keys())
    if missing:
        raise ProfileAnalysisError(f"Patient profile is missing required fields: {', '.join(missing)}")
    invalid = sorted(name for name in required if not isinstance(patient_profile[name], dict))
    if invalid:
        raise ProfileAnalysisError(f"Patient profile fields must be objects: {', '.join(invalid)}")


def analyze_profile(patient_profile: dict[str, Any]) -> dict[str, Any]:
    """Return a structured profile using the versioned validated factor rules."""

    _require_profile_fields(patient_profile)
    context = {name: deepcopy(patient_profile[name]) for name in PROFILE_CONTEXT_FIELDS}
    context.update(
        {
            name: deepcopy(patient_profile[name])
            for name in OPTIONAL_PROFILE_CONTEXT_FIELDS
            if name in patient_profile
        }
    )
    factors: list[dict[str, Any]] = []
    missing_data: list[dict[str, str]] = []

    for definition in FACTOR_DEFINITIONS:
        observation = patient_profile[definition.source_field]
        availability = observation.get("availability")
        source_value = definition.value_reader(patient_profile)
        contribution = _validated_contribution(definition, observation, source_value, patient_profile)
        justification = _factor_justification(definition, availability)
        factors.append(
            {
                "factor_id": definition.factor_id,
                "availability": availability,
                "source_value": source_value,
                "contribution": contribution,
                "rule_status": definition.rule_status,
                "justification": justification,
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
        elif contribution is None:
            missing_data.append(
                {
                    "path": f"patient_profile.{definition.source_field}",
                    "reason": f"{definition.label} is incomplete for the validated scoring rule.",
                    "impact": "prevents_favorable_output",
                }
            )

    for context_name in PROFILE_CONTEXT_FIELDS:
        observation = patient_profile[context_name]
        availability = observation.get("availability")
        path = f"patient_profile.{context_name}"
        if availability in UNAVAILABLE_STATES and not any(item["path"] == path for item in missing_data):
            label = context_name.replace("_", " ").capitalize()
            missing_data.append(
                {
                    "path": path,
                    "reason": _missing_reason(context_name, label, availability),
                    "impact": "prevents_favorable_output",
                }
            )

    validated_partial_score = sum(
        factor["contribution"] for factor in factors if isinstance(factor["contribution"], int)
    )
    profile_score = (
        sum(factor["contribution"] for factor in factors)
        if all(isinstance(factor["contribution"], int) for factor in factors)
        else None
    )
    proposed_risk_category, category_status = _risk_category(profile_score)
    return {
        "profile_score": profile_score,
        "validated_partial_score": validated_partial_score,
        "score_status": "calculated" if profile_score is not None else "partially_calculated",
        "proposed_risk_category": proposed_risk_category,
        "category_status": category_status,
        "context": context,
        "factors": factors,
        "missing_data": missing_data,
    }
