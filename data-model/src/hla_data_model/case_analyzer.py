"""Integrate patient profile and assay history into one safe restitution."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .history_analyzer import analyze_history
from .profile_analyzer import analyze_profile


RULESET_VERSION = "PROFILE-1.0.0"


def _triggered_rules(profile: dict[str, Any], history: dict[str, Any]) -> list[str]:
    rules = ["SAFE-002", "SAFE-003", "SAFE-004"]
    if profile["missing_data"] or history["missing_data"]:
        rules.insert(0, "SAFE-001")
    if history["discordances"]:
        rules.append("DISCORDANCE-ARBITRATION")
    if history["history_pattern"] in {"evolving", "fluctuating"}:
        rules.append("TREND-CLASSIFICATION")
    return rules


def _uncertainties(profile: dict[str, Any], history: dict[str, Any]) -> list[str]:
    uncertainties: list[str] = []
    if profile["profile_score"] is None:
        uncertainties.append(
            "Some scoring inputs are missing, contradictory, or incomplete; the full profile score is unavailable."
        )
    if profile["missing_data"] or history["missing_data"]:
        uncertainties.append("Missing or contradictory source data prevents a favorable automated output.")

    summary = history["current_result_summary"]
    if summary["current_result"] == "doubtful":
        uncertainties.append("A doubtful result has no automatic interpretation.")
    if history["discordances"]:
        uncertainties.append("No validated Immucor performance table covers the current discordance.")
    if history["history_pattern"].endswith("_constant") and history["history_pattern_status"] != "validated":
        uncertainties.append(
            "The history needs three prior analyses plus the current analysis over at least three years, "
            "and the 50 percent MFI proximity rule cannot be evaluated without longitudinal MFI values."
        )
    if history["history_pattern"] in {"evolving", "fluctuating"}:
        uncertainties.append(
            "No validated ordinal formula converts source categories into an increasing or decreasing trend."
        )
    if (
        history["history_pattern"] == "indeterminate"
        and not history["missing_data"]
        and not history["discordances"]
    ):
        uncertainties.append("The available history is insufficient for a validated longitudinal classification.")
    return uncertainties


def _is_simplified_review_candidate(profile: dict[str, Any], history: dict[str, Any]) -> bool:
    return (
        profile["proposed_risk_category"] == "minimal"
        and profile["category_status"] == "validated"
        and not profile["missing_data"]
        and history["history_pattern"].endswith("_constant")
        and history["history_pattern_status"] == "validated"
        and not history["missing_data"]
        and not history["discordances"]
    )


def analyze_case(source: dict[str, Any]) -> dict[str, Any]:
    """Build a full restitution from one validated synthetic source case.

    This integration combines the versioned profile score and assay-history
    description. It never emits an autonomous clinical validation.
    """

    profile = analyze_profile(source["patient_profile"])
    history = analyze_history(source["serums"])
    profile["missing_data"] = [*profile["missing_data"], *history["missing_data"]]
    simplified_review_candidate = _is_simplified_review_candidate(profile, history)
    review_status = (
        "blocked"
        if history["discordances"]
        else "candidate_for_simplified_review"
        if simplified_review_candidate
        else "human_review_required"
    )
    category = profile["proposed_risk_category"]
    review_route = (
        "discordance_blocked"
        if history["discordances"]
        else "mandatory_professional_review_uncertain"
        if category == "uncertain"
        else "manual_biologist_review"
        if category == "very_high"
        else "simplified_review_candidate"
        if simplified_review_candidate
        else "supervised_full_dossier_review"
    )

    return {
        "case_id": source["case_id"],
        "synthetic": source["synthetic"],
        "phase": source["phase"],
        "profile": profile,
        "assays": history["assays"],
        "current_result_summary": history["current_result_summary"],
        "history_pattern": history["history_pattern"],
        "history_pattern_status": history["history_pattern_status"],
        "trend": history["trend"],
        "discordances": history["discordances"],
        "review_status": review_status,
        "review_route": review_route,
        "candidate_for_simplified_review": simplified_review_candidate,
        "triggered_rules": _triggered_rules(profile, history),
        "ruleset_version": RULESET_VERSION,
        "uncertainties": _uncertainties(profile, history),
        "human_validation_required": True,
        "provenance": deepcopy(source["provenance"]),
    }
