"""Build leakage-aware ML features, simulated labels, and deterministic splits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .history_analyzer import analyze_history
from .validator import validate_scenario_pair


FEATURE_SCHEMA_VERSION = "0.1.0"
DEFAULT_SPLIT_SEED = 20261114
JOIN_KEY = "case_id"
FEATURE_COLUMNS = (
    "phase",
    "age_value",
    "age_missing",
    "sex_at_birth",
    "pregnancy_count",
    "pregnancy_missing",
    "transfusion_count",
    "transfusion_frequency",
    "transfusion_missing",
    "diabetes_state",
    "hypertension_state",
    "autoimmune_disease_state",
    "dialysis_status",
    "dialysis_duration_days",
    "rejection_suspicion_state",
    "organ_status",
    "registration_duration_days",
    "previous_transplant_count",
    "car_t_treatment_count",
    "therapeutic_antibody_treatment_count",
    "profile_unavailable_count",
    "serum_count",
    "assay_count",
    "screening_count",
    "single_antigen_count",
    "negative_result_count",
    "positive_result_count",
    "doubtful_result_count",
    "missing_result_count",
    "same_serum_discordance_count",
    "result_transition_count",
    "latest_result",
    "latest_result_status",
)
LABEL_COLUMNS = (
    "label_profile_score",
    "label_risk_category",
    "label_history_pattern",
    "label_review_route",
    "label_blocked",
    "label_candidate_for_simplified_review",
    "label_status",
    "ruleset_version",
)


class FeaturePipelineError(ValueError):
    """Raised when feature extraction would be invalid or leak unsafe data."""


def _load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FeaturePipelineError(f"JSONL file does not exist: {path}")
    records: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise FeaturePipelineError(f"{path.name}:{line_number}: invalid JSON: {error.msg}") from error
        if not isinstance(record, dict) or not isinstance(record.get("case_id"), str):
            raise FeaturePipelineError(f"{path.name}:{line_number}: record must have a string case_id")
        case_id = record["case_id"]
        if case_id in records:
            raise FeaturePipelineError(f"{path.name}:{line_number}: duplicate case_id {case_id}")
        records[case_id] = record
    return records


def _availability_value(observation: dict[str, Any], key: str = "value") -> Any:
    return observation.get(key) if observation.get("availability") == "known" else ""


def _state(observation: dict[str, Any]) -> str:
    availability = observation.get("availability")
    if availability != "known":
        return str(availability)
    value = observation.get("value")
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _days_between(evaluation_time: str, start_date: str | None) -> int | str:
    if start_date is None:
        return ""
    evaluation = datetime.fromisoformat(evaluation_time.replace("Z", "+00:00")).date()
    start = date.fromisoformat(start_date)
    return (evaluation - start).days


def _result_transition_count(serums: list[dict[str, Any]]) -> int:
    observed: list[str | None] = []
    for serum in sorted(serums, key=lambda item: item["collected_at"]):
        present = {
            assay["source_result"]
            for assay in serum["assays"]
            if assay["result_availability"] == "present"
        }
        has_missing = any(assay["result_availability"] == "missing" for assay in serum["assays"])
        observed.append(next(iter(present)) if len(present) == 1 and not has_missing else None)
    return sum(
        previous is not None and current is not None and previous != current
        for previous, current in zip(observed, observed[1:])
    )


def _extract_features(source: dict[str, Any]) -> dict[str, Any]:
    profile = source["patient_profile"]
    assays = [assay for serum in source["serums"] for assay in serum["assays"]]
    history = analyze_history(source["serums"])
    latest = history["current_result_summary"]
    unavailable_count = sum(
        isinstance(value, dict) and value.get("availability") in {"missing", "contradictory"}
        for value in profile.values()
    )
    return {
        "phase": source["phase"],
        "age_value": _availability_value(profile["age"]),
        "age_missing": int(profile["age"]["availability"] != "known"),
        "sex_at_birth": _availability_value(profile["sex_at_birth"]),
        "pregnancy_count": _availability_value(profile["pregnancy_history"], "count"),
        "pregnancy_missing": int(profile["pregnancy_history"]["availability"] != "known"),
        "transfusion_count": _availability_value(profile["transfusion_history"], "count"),
        "transfusion_frequency": _availability_value(profile["transfusion_history"], "frequency"),
        "transfusion_missing": int(profile["transfusion_history"]["availability"] != "known"),
        "diabetes_state": _state(profile["diabetes"]),
        "hypertension_state": _state(profile["hypertension"]),
        "autoimmune_disease_state": _state(profile["autoimmune_disease"]),
        "dialysis_status": _availability_value(profile["dialysis"], "status"),
        "dialysis_duration_days": _days_between(source["evaluation_time"], profile["dialysis"].get("started_at")),
        "rejection_suspicion_state": _state(profile["rejection_suspicion"]),
        "organ_status": _availability_value(profile["organ_context"], "status"),
        "registration_duration_days": _days_between(
            source["evaluation_time"], profile["organ_context"].get("registration_date")
        ),
        "previous_transplant_count": len(profile["previous_transplants"]["events"]),
        "car_t_treatment_count": len(profile["car_t_treatments"]["events"]),
        "therapeutic_antibody_treatment_count": len(profile["therapeutic_antibody_treatments"]["events"]),
        "profile_unavailable_count": unavailable_count,
        "serum_count": len(source["serums"]),
        "assay_count": len(assays),
        "screening_count": sum(assay["test_type"] == "screening" for assay in assays),
        "single_antigen_count": sum(assay["test_type"] == "single_antigen" for assay in assays),
        "negative_result_count": sum(assay["source_result"] == "negative" for assay in assays),
        "positive_result_count": sum(assay["source_result"] == "positive" for assay in assays),
        "doubtful_result_count": sum(assay["source_result"] == "doubtful" for assay in assays),
        "missing_result_count": sum(assay["result_availability"] == "missing" for assay in assays),
        "same_serum_discordance_count": len(history["discordances"]),
        "result_transition_count": _result_transition_count(source["serums"]),
        "latest_result": latest["current_result"] or "",
        "latest_result_status": latest["status"],
    }


def _extract_labels(restitution: dict[str, Any]) -> dict[str, Any]:
    profile = restitution["profile"]
    return {
        "label_profile_score": "" if profile["profile_score"] is None else profile["profile_score"],
        "label_risk_category": profile["proposed_risk_category"],
        "label_history_pattern": restitution["history_pattern"],
        "label_review_route": restitution["review_status"],
        "label_blocked": int(restitution["review_status"] == "blocked"),
        "label_candidate_for_simplified_review": int(restitution["candidate_for_simplified_review"]),
        "label_status": "simulation_only",
        "ruleset_version": restitution["ruleset_version"],
    }


def _hash_order(case_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{case_id}".encode("utf-8")).hexdigest()


def _build_splits(sources: dict[str, dict[str, Any]], seed: int) -> dict[str, str]:
    groups: dict[str, list[str]] = defaultdict(list)
    for case_id, source in sources.items():
        scenario = source["provenance"].get("simulation_scenario")
        if not isinstance(scenario, str):
            raise FeaturePipelineError(f"{case_id}: simulation_scenario is required for stratified splitting")
        groups[scenario].append(case_id)
    if any(len(case_ids) < 3 for case_ids in groups.values()):
        raise FeaturePipelineError("Every simulation scenario needs at least three cases for train/validation/test")

    counts = {scenario: {"validation": 1, "test": 1, "train": len(case_ids) - 2} for scenario, case_ids in groups.items()}
    total = len(sources)
    targets = {"validation": round(total * 0.15), "test": round(total * 0.15)}
    scenario_order = sorted(groups, key=lambda scenario: (-len(groups[scenario]), scenario))
    for split in ("validation", "test"):
        deficit = targets[split] - sum(value[split] for value in counts.values())
        cursor = 0
        while deficit > 0:
            scenario = scenario_order[cursor % len(scenario_order)]
            if counts[scenario]["train"] > 1:
                counts[scenario]["train"] -= 1
                counts[scenario][split] += 1
                deficit -= 1
            cursor += 1

    assignments: dict[str, str] = {}
    for scenario in sorted(groups):
        case_ids = sorted(groups[scenario], key=lambda case_id: _hash_order(case_id, seed))
        validation_count = counts[scenario]["validation"]
        test_count = counts[scenario]["test"]
        for index, case_id in enumerate(case_ids):
            assignments[case_id] = (
                "validation"
                if index < validation_count
                else "test"
                if index < validation_count + test_count
                else "train"
            )
    return assignments


def _csv_text(rows: list[dict[str, Any]], fieldnames: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_feature_dataset(
    source_path: Path,
    restitution_path: Path,
    features_path: Path,
    labels_path: Path,
    splits_path: Path,
    manifest_path: Path,
    split_seed: int = DEFAULT_SPLIT_SEED,
) -> dict[str, Any]:
    """Build separate feature, label, and split artifacts with leakage controls."""

    paths = [source_path, restitution_path, features_path, labels_path, splits_path, manifest_path]
    if len({path.resolve() for path in paths}) != len(paths):
        raise FeaturePipelineError("All feature-pipeline input and output paths must be distinct")
    sources = _load_jsonl(source_path)
    restitutions = _load_jsonl(restitution_path)
    if set(sources) != set(restitutions):
        missing_restitutions = sorted(set(sources) - set(restitutions))
        missing_sources = sorted(set(restitutions) - set(sources))
        raise FeaturePipelineError(
            f"Source/restitution case_id mismatch; missing restitutions={missing_restitutions}, missing sources={missing_sources}"
        )

    assignments = _build_splits(sources, split_seed)
    feature_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    for case_id in sorted(sources):
        source = sources[case_id]
        restitution = restitutions[case_id]
        validate_scenario_pair(source, restitution)
        feature_rows.append({JOIN_KEY: case_id, **_extract_features(source)})
        label_rows.append({JOIN_KEY: case_id, **_extract_labels(restitution)})
        split_rows.append({JOIN_KEY: case_id, "split": assignments[case_id]})

    feature_text = _csv_text(feature_rows, (JOIN_KEY, *FEATURE_COLUMNS))
    label_text = _csv_text(label_rows, (JOIN_KEY, *LABEL_COLUMNS))
    split_text = _csv_text(split_rows, (JOIN_KEY, "split"))
    split_counts = {split: list(assignments.values()).count(split) for split in ("train", "validation", "test")}
    manifest = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "row_count": len(feature_rows),
        "join_key": JOIN_KEY,
        "feature_columns": list(FEATURE_COLUMNS),
        "label_columns": list(LABEL_COLUMNS),
        "label_status": "simulation_only",
        "clinical_performance_claim_allowed": False,
        "split_seed": split_seed,
        "split_method": "deterministic_stratification_by_simulation_scenario_for_coverage_only",
        "split_counts": split_counts,
        "excluded_from_features": [
            "case_id",
            "provenance.*",
            "simulation_scenario",
            "profile_score",
            "risk_category",
            "history_pattern",
            "review_route",
            "ruleset_version",
            "post_evaluation_data",
        ],
        "files": {
            "features": {"name": features_path.name, "sha256": _sha256_text(feature_text)},
            "labels": {"name": labels_path.name, "sha256": _sha256_text(label_text)},
            "splits": {"name": splits_path.name, "sha256": _sha256_text(split_text)},
        },
    }
    for path in (features_path, labels_path, splits_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    features_path.write_text(feature_text, encoding="utf-8")
    labels_path.write_text(label_text, encoding="utf-8")
    splits_path.write_text(split_text, encoding="utf-8")
    manifest_path.write_text(f"{json.dumps(manifest, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--restitutions", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-seed", type=int, default=DEFAULT_SPLIT_SEED)
    args = parser.parse_args()
    manifest = build_feature_dataset(
        args.sources,
        args.restitutions,
        args.features,
        args.labels,
        args.splits,
        args.manifest,
        split_seed=args.split_seed,
    )
    print(f"Built {manifest['row_count']} feature rows with splits {manifest['split_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
