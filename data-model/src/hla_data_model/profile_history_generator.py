"""Attach deterministic synthetic assay histories to imported patient profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .generator import DEFAULT_SEED, write_jsonl
from .validator import validate_source_case


HISTORY_GENERATOR_VERSION = "profile-history-generator-v1"
HISTORY_SCENARIOS = (
    "negative_constant",
    "positive_constant",
    "doubtful_constant",
    "negative_to_positive",
    "positive_to_negative",
    "fluctuating",
    "missing_result",
    "same_serum_discordance",
)


class ProfileHistoryGenerationError(ValueError):
    """Raised when histories cannot be attached without overwriting source facts."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _scenario_results(scenario: str) -> list[list[str | None]]:
    return {
        "negative_constant": [["negative"], ["negative"], ["negative"]],
        "positive_constant": [["positive"], ["positive"], ["positive"]],
        "doubtful_constant": [["doubtful"], ["doubtful"], ["doubtful"]],
        "negative_to_positive": [["negative"], ["negative"], ["positive"]],
        "positive_to_negative": [["positive"], ["positive"], ["negative"]],
        "fluctuating": [["negative"], ["positive"], ["negative"]],
        "missing_result": [["negative"], ["negative"], [None]],
        "same_serum_discordance": [["negative"], ["negative", "positive"]],
    }[scenario]


def _build_serums(evaluation_time: str, scenario: str) -> list[dict[str, Any]]:
    evaluation = datetime.fromisoformat(evaluation_time.replace("Z", "+00:00"))
    result_groups = _scenario_results(scenario)
    serums: list[dict[str, Any]] = []
    assay_number = 1
    for serum_offset, results in enumerate(result_groups, start=1):
        days_before = (len(result_groups) - serum_offset + 1) * 60
        collected_at = evaluation - timedelta(days=days_before, hours=2)
        assays: list[dict[str, Any]] = []
        for result_offset, result in enumerate(results):
            assay_id = f"ASSAY-{assay_number:03d}"
            assay_number += 1
            assays.append(
                {
                    "assay_id": assay_id,
                    "test_type": "screening" if result_offset == 0 else "single_antigen",
                    "manufacturer": "Immucor",
                    "result_availability": "missing" if result is None else "present",
                    "source_result": result,
                    "performed_at": None
                    if result is None
                    else _iso(collected_at + timedelta(hours=4 + result_offset)),
                    "kit_reference": "SYN-IMM-HISTORY-V1",
                    "lot": None if result is None else f"SYN-HIST-LOT-{serum_offset:02d}-{result_offset + 1:02d}",
                    "quality_status": "unknown" if result is None else "pending_review",
                }
            )
        serums.append(
            {
                "serum_id": f"SER-{serum_offset:03d}",
                "collected_at": _iso(collected_at),
                "assays": assays,
            }
        )
    return serums


def _scenario_assignments(case_ids: list[str], seed: int) -> dict[str, str]:
    scenarios = [HISTORY_SCENARIOS[index % len(HISTORY_SCENARIOS)] for index in range(len(case_ids))]
    random.Random(seed).shuffle(scenarios)
    return dict(zip(sorted(case_ids), scenarios))


def _load_sources(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ProfileHistoryGenerationError(f"Source JSONL file does not exist: {path}")
    sources: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            source = json.loads(line)
        except json.JSONDecodeError as error:
            raise ProfileHistoryGenerationError(f"{path.name}:{line_number}: invalid JSON: {error.msg}") from error
        case_id = source.get("case_id") if isinstance(source, dict) else None
        if not isinstance(case_id, str):
            raise ProfileHistoryGenerationError(f"{path.name}:{line_number}: missing string case_id")
        if case_id in seen_ids:
            raise ProfileHistoryGenerationError(f"{path.name}:{line_number}: duplicate case_id {case_id}")
        if source.get("synthetic") is not True:
            raise ProfileHistoryGenerationError(f"{case_id}: only explicitly synthetic profiles are accepted")
        if source.get("serums"):
            raise ProfileHistoryGenerationError(f"{case_id}: existing serum history cannot be overwritten")
        seen_ids.add(case_id)
        sources.append(source)
    return sources


def generate_profile_histories(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Attach coverage-balanced histories without changing imported profiles."""

    if len({input_path.resolve(), output_path.resolve(), report_path.resolve()}) != 3:
        raise ProfileHistoryGenerationError("Input, output, and report paths must be distinct")
    input_bytes = input_path.read_bytes() if input_path.is_file() else b""
    sources = _load_sources(input_path)
    assignments = _scenario_assignments([source["case_id"] for source in sources], seed)
    generated: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for original in sorted(sources, key=lambda item: item["case_id"]):
        source = deepcopy(original)
        scenario = assignments[source["case_id"]]
        source["serums"] = _build_serums(source["evaluation_time"], scenario)
        original_generator = source["provenance"].get("generator_version")
        source["provenance"] = {
            **source["provenance"],
            "generator_version": HISTORY_GENERATOR_VERSION,
            "profile_importer_version": original_generator,
            "simulation_scenario": scenario,
        }
        validate_source_case(source)
        generated.append(source)
        counts[scenario] += 1

    output_text = "".join(f"{json.dumps(source, ensure_ascii=False, sort_keys=True)}\n" for source in generated)
    report = {
        "generator_version": HISTORY_GENERATOR_VERSION,
        "seed": seed,
        "input_file": input_path.name,
        "input_sha256": _sha256(input_bytes),
        "output_file": output_path.name,
        "output_sha256": _sha256(output_text.encode("utf-8")),
        "record_count": len(generated),
        "scenario_counts": {scenario: counts[scenario] for scenario in HISTORY_SCENARIOS},
        "scenario_quota_meaning": "synthetic_coverage_only_not_clinical_prevalence",
        "trend_interpretation": "indeterminate_without_validated_ordinal_rule",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")
    report_path.write_text(f"{json.dumps(report, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    report = generate_profile_histories(args.input, args.output, args.report, seed=args.seed)
    print(f"Generated {report['record_count']} longitudinal histories in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
