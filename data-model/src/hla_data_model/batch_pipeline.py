"""Validate a source JSONL dataset and produce restitutions plus a quality report."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .case_analyzer import analyze_case
from .validator import ValidationError, validate_source_case


DATASET_VERSION = "0.2.0"
RISK_CATEGORIES = ("minimal", "moderate", "medium", "high", "very_high", "uncertain")
SCORE_STATUSES = ("partially_calculated", "calculated", "validated")
CURRENT_RESULTS = ("negative", "positive", "doubtful", "data_missing", "discordance_unresolved")
HISTORY_PATTERNS = (
    "negative_constant",
    "positive_constant",
    "doubtful_constant",
    "evolving",
    "fluctuating",
    "indeterminate",
)
REVIEW_ROUTES = ("human_review_required", "candidate_for_simplified_review", "blocked")
PHASES = ("pre_transplant", "post_transplant")


class BatchPipelineError(ValueError):
    """Raised when batch input/output configuration is unsafe or invalid."""


def _counts(counter: Counter[str], values: Iterable[str]) -> dict[str, int]:
    return {value: counter.get(value, 0) for value in values}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current_result_key(restitution: dict[str, Any]) -> str:
    summary = restitution["current_result_summary"]
    if summary["status"] == "discordance_unresolved":
        return "discordance_unresolved"
    if summary["current_result"] is None:
        return "data_missing"
    return summary["current_result"]


def _assert_distinct_paths(input_path: Path, restitution_path: Path, report_path: Path) -> None:
    resolved = [path.resolve() for path in (input_path, restitution_path, report_path)]
    if len(set(resolved)) != len(resolved):
        raise BatchPipelineError("Input, restitution output, and report output must use distinct paths")


def process_jsonl_dataset(
    input_path: Path,
    restitution_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Process each JSONL record independently and write deterministic outputs."""

    _assert_distinct_paths(input_path, restitution_path, report_path)
    if not input_path.is_file():
        raise BatchPipelineError(f"Input file does not exist: {input_path}")

    input_bytes = input_path.read_bytes()
    input_lines = input_bytes.decode("utf-8").splitlines()
    restitutions: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()

    score_statuses: Counter[str] = Counter()
    risk_categories: Counter[str] = Counter()
    current_results: Counter[str] = Counter()
    history_patterns: Counter[str] = Counter()
    review_routes: Counter[str] = Counter()
    phases: Counter[str] = Counter()
    ruleset_versions: Counter[str] = Counter()
    generator_versions: Counter[str] = Counter()
    simulation_scenarios: Counter[str] = Counter()
    cases_with_missing_data = 0
    missing_data_entries = 0
    cases_with_discordance = 0
    discordance_count = 0

    for line_number, raw_line in enumerate(input_lines, start=1):
        case_id: str | None = None
        if not raw_line.strip():
            errors.append({"line": line_number, "case_id": None, "errors": ["Empty JSONL record"]})
            continue
        try:
            source = json.loads(raw_line)
        except json.JSONDecodeError as error:
            errors.append(
                {
                    "line": line_number,
                    "case_id": None,
                    "errors": [f"Invalid JSON: {error.msg}"],
                }
            )
            continue
        if not isinstance(source, dict):
            errors.append({"line": line_number, "case_id": None, "errors": ["JSONL record must be an object"]})
            continue
        raw_case_id = source.get("case_id")
        case_id = raw_case_id if isinstance(raw_case_id, str) else None
        if case_id is not None and case_id in seen_case_ids:
            errors.append({"line": line_number, "case_id": case_id, "errors": ["Duplicate case_id"]})
            continue
        try:
            validate_source_case(source)
            restitution = analyze_case(source)
        except (ValidationError, KeyError, TypeError, ValueError) as error:
            error_messages = error.errors if isinstance(error, ValidationError) else [str(error)]
            errors.append({"line": line_number, "case_id": case_id, "errors": error_messages})
            continue

        seen_case_ids.add(restitution["case_id"])
        restitutions.append(restitution)
        profile = restitution["profile"]
        score_statuses[profile["score_status"]] += 1
        risk_categories[profile["proposed_risk_category"]] += 1
        current_results[_current_result_key(restitution)] += 1
        history_patterns[restitution["history_pattern"]] += 1
        review_routes[restitution["review_status"]] += 1
        phases[restitution["phase"]] += 1
        ruleset_versions[restitution["ruleset_version"]] += 1
        generator_versions[restitution["provenance"]["generator_version"]] += 1
        simulation_scenario = restitution["provenance"].get("simulation_scenario")
        if isinstance(simulation_scenario, str):
            simulation_scenarios[simulation_scenario] += 1
        current_missing_count = len(profile["missing_data"])
        if current_missing_count:
            cases_with_missing_data += 1
            missing_data_entries += current_missing_count
        current_discordance_count = len(restitution["discordances"])
        if current_discordance_count:
            cases_with_discordance += 1
            discordance_count += current_discordance_count

    restitution_text = "".join(
        f"{json.dumps(restitution, ensure_ascii=False, sort_keys=True)}\n"
        for restitution in restitutions
    )
    report = {
        "dataset_version": DATASET_VERSION,
        "input_file": input_path.name,
        "input_sha256": _sha256(input_bytes),
        "restitutions_file": restitution_path.name,
        "restitutions_sha256": _sha256(restitution_text.encode("utf-8")),
        "total_records": len(input_lines),
        "valid_records": len(restitutions),
        "invalid_records": len(errors),
        "phases": _counts(phases, PHASES),
        "profile": {
            "score_statuses": _counts(score_statuses, SCORE_STATUSES),
            "risk_categories": _counts(risk_categories, RISK_CATEGORIES),
        },
        "assays": {"current_results": _counts(current_results, CURRENT_RESULTS)},
        "history_patterns": _counts(history_patterns, HISTORY_PATTERNS),
        "review_routes": _counts(review_routes, REVIEW_ROUTES),
        "quality": {
            "cases_with_missing_data": cases_with_missing_data,
            "missing_data_entries": missing_data_entries,
            "cases_with_discordance": cases_with_discordance,
            "discordance_count": discordance_count,
        },
        "ruleset_versions": dict(sorted(ruleset_versions.items())),
        "generator_versions": dict(sorted(generator_versions.items())),
        "simulation_scenarios": dict(sorted(simulation_scenarios.items())),
        "errors": errors,
    }

    restitution_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    restitution_path.write_text(restitution_text, encoding="utf-8")
    report_path.write_text(
        f"{json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--restitutions", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = process_jsonl_dataset(args.input, args.restitutions, args.report)
    print(
        f"Processed {report['total_records']} records: "
        f"{report['valid_records']} valid, {report['invalid_records']} invalid"
    )
    return 1 if report["invalid_records"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
