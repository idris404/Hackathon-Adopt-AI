"""Validate HLA Twin source/expected scenario pairs without medical inference."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


RULESET_VERSION = "DEMO-PENDING-0.1.0"
SOURCE_RESULTS = {"negative", "positive", "doubtful"}
PHASES = {"pre_transplant", "post_transplant"}
PROFILE_PATHS = {
    "PF-01": "age",
    "PF-02": "pregnancy_history",
    "PF-03": "diabetes",
    "PF-04": "hypertension",
    "PF-05": "autoimmune_disease",
    "PF-06": "previous_transplants",
    "PF-07": "transfusion_history",
}
DERIVED_SOURCE_KEYS = {
    "profile_score",
    "proposed_risk_category",
    "candidate_for_simplified_review",
    "history_pattern",
    "trend",
    "triggered_rules",
}


class ValidationError(ValueError):
    """Raised when a scenario violates its contract or a safety invariant."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def _require_keys(value: dict[str, Any], keys: set[str], path: str, errors: list[str]) -> None:
    missing = sorted(keys - value.keys())
    errors.extend(f"{path}.{key}: required field is missing" for key in missing)


def _parse_datetime(value: Any, path: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{path}: expected an ISO 8601 date-time string")
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: invalid ISO 8601 date-time")
        return None


def _find_derived_keys(value: Any, path: str = "source") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in DERIVED_SOURCE_KEYS:
                found.append(child_path)
            found.extend(_find_derived_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_derived_keys(child, f"{path}[{index}]"))
    return found


def _source_assays(source: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    assay_index: dict[str, dict[str, Any]] = {}
    evaluation_time = _parse_datetime(source.get("evaluation_time"), "source.evaluation_time", errors)

    serums = source.get("serums")
    if not isinstance(serums, list):
        errors.append("source.serums: expected a list")
        return assay_index

    serum_ids: set[str] = set()
    for serum_index, serum in enumerate(serums):
        serum_path = f"source.serums[{serum_index}]"
        if not isinstance(serum, dict):
            errors.append(f"{serum_path}: expected an object")
            continue
        _require_keys(serum, {"serum_id", "collected_at", "assays"}, serum_path, errors)
        serum_id = serum.get("serum_id")
        if not isinstance(serum_id, str):
            errors.append(f"{serum_path}.serum_id: expected a string")
            continue
        if serum_id in serum_ids:
            errors.append(f"{serum_path}.serum_id: duplicate identifier {serum_id}")
        serum_ids.add(serum_id)
        collected_at = _parse_datetime(serum.get("collected_at"), f"{serum_path}.collected_at", errors)
        if evaluation_time and collected_at and collected_at > evaluation_time:
            errors.append(f"{serum_path}.collected_at: occurs after evaluation_time")

        assays = serum.get("assays")
        if not isinstance(assays, list):
            errors.append(f"{serum_path}.assays: expected a list")
            continue
        for assay_position, assay in enumerate(assays):
            assay_path = f"{serum_path}.assays[{assay_position}]"
            if not isinstance(assay, dict):
                errors.append(f"{assay_path}: expected an object")
                continue
            _require_keys(
                assay,
                {
                    "assay_id",
                    "test_type",
                    "manufacturer",
                    "result_availability",
                    "source_result",
                    "performed_at",
                    "kit_reference",
                    "lot",
                    "quality_status",
                },
                assay_path,
                errors,
            )
            assay_id = assay.get("assay_id")
            if not isinstance(assay_id, str):
                errors.append(f"{assay_path}.assay_id: expected a string")
                continue
            if assay_id in assay_index:
                errors.append(f"{assay_path}.assay_id: duplicate identifier {assay_id}")
            availability = assay.get("result_availability")
            result = assay.get("source_result")
            if availability == "missing" and result is not None:
                errors.append(f"{assay_path}: a missing result must be null, never negative")
            if availability == "present" and result not in SOURCE_RESULTS:
                errors.append(f"{assay_path}: a present result must use a source result category")
            if availability not in {"present", "missing"}:
                errors.append(f"{assay_path}.result_availability: invalid value")
            if assay.get("manufacturer") != "Immucor":
                errors.append(f"{assay_path}.manufacturer: demo contract currently supports Immucor only")
            performed_at_raw = assay.get("performed_at")
            if performed_at_raw is not None:
                performed_at = _parse_datetime(performed_at_raw, f"{assay_path}.performed_at", errors)
                if evaluation_time and performed_at and performed_at > evaluation_time:
                    errors.append(f"{assay_path}.performed_at: occurs after evaluation_time")
            assay_index[assay_id] = {**assay, "serum_id": serum_id}
    return assay_index


def _validate_source(source: dict[str, Any], errors: list[str]) -> dict[str, dict[str, Any]]:
    _require_keys(
        source,
        {"case_id", "synthetic", "schema_version", "phase", "evaluation_time", "patient_profile", "serums", "provenance"},
        "source",
        errors,
    )
    if source.get("synthetic") is not True:
        errors.append("source.synthetic: must be true")
    if source.get("schema_version") != "0.1.0":
        errors.append("source.schema_version: unsupported version")
    if source.get("phase") not in PHASES:
        errors.append("source.phase: invalid phase")
    for path in _find_derived_keys(source):
        errors.append(f"{path}: derived output must not appear in source data")

    profile = source.get("patient_profile")
    if not isinstance(profile, dict):
        errors.append("source.patient_profile: expected an object")
    else:
        _require_keys(
            profile,
            {
                "age",
                "pregnancy_history",
                "transfusion_history",
                "diabetes",
                "hypertension",
                "autoimmune_disease",
                "previous_transplants",
                "antibody_based_treatments",
            },
            "source.patient_profile",
            errors,
        )
        for name, observation in profile.items():
            if not isinstance(observation, dict):
                errors.append(f"source.patient_profile.{name}: expected an object")
                continue
            availability = observation.get("availability")
            if availability not in {"known", "missing", "not_applicable", "contradictory"}:
                errors.append(f"source.patient_profile.{name}.availability: invalid value")
            if availability in {"missing", "contradictory"}:
                scalar_value = observation.get("value", observation.get("count"))
                if scalar_value is not None:
                    errors.append(f"source.patient_profile.{name}: unavailable scalar value must be null")

    provenance = source.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source_record_copied") is not False:
        errors.append("source.provenance.source_record_copied: must be false")
    return _source_assays(source, errors)


def _validate_restitution(
    source: dict[str, Any],
    restitution: dict[str, Any],
    source_assays: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    _require_keys(
        restitution,
        {
            "case_id",
            "synthetic",
            "phase",
            "profile",
            "assays",
            "history_pattern",
            "history_pattern_status",
            "trend",
            "discordances",
            "review_status",
            "candidate_for_simplified_review",
            "triggered_rules",
            "ruleset_version",
            "uncertainties",
            "human_validation_required",
            "provenance",
        },
        "restitution",
        errors,
    )
    if restitution.get("case_id") != source.get("case_id"):
        errors.append("restitution.case_id: must match the source case")
    if restitution.get("phase") != source.get("phase"):
        errors.append("restitution.phase: must match the source phase")
    if restitution.get("synthetic") is not True:
        errors.append("restitution.synthetic: must be true")
    if restitution.get("human_validation_required") is not True:
        errors.append("restitution.human_validation_required: must be true")
    if restitution.get("ruleset_version") != RULESET_VERSION:
        errors.append("restitution.ruleset_version: unsupported or unknown ruleset")
    if restitution.get("candidate_for_simplified_review") is not False:
        errors.append("restitution.candidate_for_simplified_review: must remain false while rules are unvalidated")
    if restitution.get("review_status") == "candidate_for_simplified_review":
        errors.append("restitution.review_status: simplified review is not allowed with the pending ruleset")

    profile = restitution.get("profile")
    if not isinstance(profile, dict):
        errors.append("restitution.profile: expected an object")
        return
    if profile.get("profile_score") is not None:
        errors.append("restitution.profile.profile_score: must be null while factor weights are unvalidated")
    if profile.get("score_status") != "pending_review":
        errors.append("restitution.profile.score_status: must be pending_review")
    if profile.get("proposed_risk_category") != "uncertain":
        errors.append("restitution.profile.proposed_risk_category: must be uncertain while the score is unavailable")
    if profile.get("category_status") != "pending_review":
        errors.append("restitution.profile.category_status: must be pending_review")

    factors = profile.get("factors")
    factor_index: dict[str, dict[str, Any]] = {}
    if not isinstance(factors, list):
        errors.append("restitution.profile.factors: expected a list")
    else:
        for position, factor in enumerate(factors):
            factor_path = f"restitution.profile.factors[{position}]"
            if not isinstance(factor, dict):
                errors.append(f"{factor_path}: expected an object")
                continue
            factor_id = factor.get("factor_id")
            if not isinstance(factor_id, str):
                errors.append(f"{factor_path}.factor_id: expected a string")
                continue
            if factor_id in factor_index:
                errors.append(f"{factor_path}.factor_id: duplicate identifier {factor_id}")
            factor_index[factor_id] = factor
            if factor.get("contribution") is not None:
                errors.append(f"{factor_path}.contribution: must be null until its rule is validated")

    source_profile = source.get("patient_profile", {})
    for factor_id, source_name in PROFILE_PATHS.items():
        source_observation = source_profile.get(source_name, {})
        restitution_factor = factor_index.get(factor_id)
        if restitution_factor is None:
            errors.append(f"restitution.profile.factors: missing {factor_id}")
            continue
        if restitution_factor.get("availability") != source_observation.get("availability"):
            errors.append(f"restitution.profile.factors.{factor_id}.availability: must preserve the source state")

    missing_paths = {
        item.get("path")
        for item in profile.get("missing_data", [])
        if isinstance(item, dict)
    }
    for factor_id, source_name in PROFILE_PATHS.items():
        observation = source_profile.get(source_name, {})
        if observation.get("availability") in {"missing", "contradictory"}:
            expected_path = f"patient_profile.{source_name}"
            if expected_path not in missing_paths:
                errors.append(f"restitution.profile.missing_data: must include {expected_path}")

    restitution_assays = restitution.get("assays")
    restitution_index: dict[str, dict[str, Any]] = {}
    if not isinstance(restitution_assays, list):
        errors.append("restitution.assays: expected a list")
    else:
        for position, assay in enumerate(restitution_assays):
            if not isinstance(assay, dict):
                errors.append(f"restitution.assays[{position}]: expected an object")
                continue
            assay_id = assay.get("assay_id")
            if isinstance(assay_id, str):
                restitution_index[assay_id] = assay
        if set(restitution_index) != set(source_assays):
            errors.append("restitution.assays: must contain exactly the source assays")

    for assay_id, source_assay in source_assays.items():
        expected = restitution_index.get(assay_id)
        if expected is None:
            continue
        for key in ("serum_id", "result_availability", "source_result"):
            if expected.get(key) != source_assay.get(key):
                errors.append(f"restitution.assays.{assay_id}.{key}: must preserve the source value")
        if source_assay.get("result_availability") == "missing":
            missing_path = f"serums.{source_assay['serum_id']}.assays.{assay_id}.source_result"
            if missing_path not in missing_paths:
                errors.append(f"restitution.profile.missing_data: must include {missing_path}")

    all_assays_negative = bool(source_assays) and all(
        assay.get("result_availability") == "present" and assay.get("source_result") == "negative"
        for assay in source_assays.values()
    )
    if restitution.get("history_pattern") == "negative_constant" and not all_assays_negative:
        errors.append("restitution.history_pattern: negative_constant requires every available assay to be present and negative")
    if restitution.get("history_pattern_status") != "pending_review":
        errors.append("restitution.history_pattern_status: must remain pending_review")


def validate_scenario_pair(source: dict[str, Any], restitution: dict[str, Any]) -> None:
    """Validate a source case and its expected restitution.

    The function deliberately performs no medical calculation.
    """

    errors: list[str] = []
    source_copy = deepcopy(source)
    restitution_copy = deepcopy(restitution)
    source_assays = _validate_source(source_copy, errors)
    _validate_restitution(source_copy, restitution_copy, source_assays, errors)
    if errors:
        raise ValidationError(errors)


def validate_scenario_directory(scenario_directory: Path) -> None:
    source_path = scenario_directory / "source.json"
    restitution_path = scenario_directory / "expected-restitution.json"
    if not source_path.is_file() or not restitution_path.is_file():
        raise ValidationError([f"{scenario_directory}: source.json and expected-restitution.json are required"])
    with source_path.open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    with restitution_path.open(encoding="utf-8") as restitution_file:
        restitution = json.load(restitution_file)
    validate_scenario_pair(source, restitution)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_root", type=Path, help="Directory containing scenario subdirectories")
    args = parser.parse_args()

    failures = 0
    scenario_directories = sorted(path for path in args.scenario_root.iterdir() if path.is_dir())
    if not scenario_directories:
        print(f"No scenarios found in {args.scenario_root}")
        return 1
    for scenario_directory in scenario_directories:
        try:
            validate_scenario_directory(scenario_directory)
        except (ValidationError, json.JSONDecodeError) as error:
            failures += 1
            print(f"FAIL {scenario_directory.name}: {error}")
        else:
            print(f"PASS {scenario_directory.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
