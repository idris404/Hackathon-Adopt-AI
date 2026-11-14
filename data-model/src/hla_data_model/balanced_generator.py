"""Generate a deterministic stratified dataset for demo and coverage testing."""

from __future__ import annotations

import argparse
import random
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any

from .generator import DEFAULT_SEED, EVALUATION_TIME, generate_source_cases, write_jsonl


SCENARIO_QUOTAS = {
    "minimal_negative_constant": 15,
    "moderate_negative_constant": 10,
    "medium_evolving": 15,
    "high_doubtful_constant": 10,
    "very_high_fluctuating": 10,
    "incomplete_missing_result": 15,
    "unresolved_profile_positive_constant": 10,
    "discordant_blocked": 10,
    "minimal_positive_constant": 5,
}


def _iso(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _clean_profile(profile: dict[str, Any]) -> None:
    profile["age"] = {"availability": "known", "value": 52}
    profile["pregnancy_history"] = {"availability": "known", "status": "none", "count": 0, "dates": []}
    profile["transfusion_history"] = {
        "availability": "known",
        "count": 0,
        "dates": [],
        "frequency": "none",
    }
    profile["diabetes"] = {"availability": "known", "value": False}
    profile["hypertension"] = {"availability": "known", "value": False}
    profile["autoimmune_disease"] = {"availability": "known", "value": False}
    profile["previous_transplants"] = {"availability": "known", "events": []}
    profile["car_t_treatments"] = {"availability": "known", "events": []}
    profile["therapeutic_antibody_treatments"] = {"availability": "known", "events": []}


def _set_profile_scenario(profile: dict[str, Any], scenario_type: str) -> None:
    _clean_profile(profile)
    if scenario_type == "moderate_negative_constant":
        profile["age"]["value"] = 66
    elif scenario_type == "medium_evolving":
        profile["pregnancy_history"].update({"status": "multiple", "count": 2})
    elif scenario_type == "high_doubtful_constant":
        profile["pregnancy_history"].update({"status": "multiple", "count": 2})
        profile["transfusion_history"].update({"count": 4, "frequency": "regular"})
    elif scenario_type == "very_high_fluctuating":
        profile["age"]["value"] = 66
        profile["pregnancy_history"].update({"status": "multiple", "count": 2})
        profile["transfusion_history"].update({"count": 4, "frequency": "regular"})
    elif scenario_type == "incomplete_missing_result":
        profile["age"] = {"availability": "missing", "value": None}
    elif scenario_type == "unresolved_profile_positive_constant":
        profile["hypertension"] = {"availability": "known", "value": True}


def _history_results(scenario_type: str) -> list[list[str | None]]:
    if scenario_type in {"minimal_negative_constant", "moderate_negative_constant"}:
        return [["negative"], ["negative"]]
    if scenario_type == "medium_evolving":
        return [["negative"], ["positive"]]
    if scenario_type == "high_doubtful_constant":
        return [["doubtful"], ["doubtful"]]
    if scenario_type == "very_high_fluctuating":
        return [["negative"], ["positive"], ["negative"]]
    if scenario_type == "incomplete_missing_result":
        return [["negative"], [None]]
    if scenario_type in {"unresolved_profile_positive_constant", "minimal_positive_constant"}:
        return [["positive"], ["positive"]]
    if scenario_type == "discordant_blocked":
        return [["negative", "positive"]]
    raise ValueError(f"Unknown balanced scenario type: {scenario_type}")


def _build_serums(
    scenario_type: str,
    serum_sequence: int,
    assay_sequence: int,
) -> tuple[list[dict[str, Any]], int, int]:
    result_groups = _history_results(scenario_type)
    serums: list[dict[str, Any]] = []
    for serum_offset, results in enumerate(result_groups):
        collected_at = EVALUATION_TIME - timedelta(days=(len(result_groups) - serum_offset) * 45, hours=1)
        serum_id = f"SER-{serum_sequence:03d}"
        serum_sequence += 1
        assays: list[dict[str, Any]] = []
        for result_offset, result in enumerate(results):
            assay_id = f"ASSAY-{assay_sequence:03d}"
            assay_sequence += 1
            assays.append(
                {
                    "assay_id": assay_id,
                    "test_type": "screening" if result_offset == 0 else "single_antigen",
                    "manufacturer": "Immucor",
                    "result_availability": "missing" if result is None else "present",
                    "source_result": result,
                    "performed_at": None if result is None else _iso(collected_at + timedelta(hours=4 + result_offset)),
                    "kit_reference": "SYN-IMM-BALANCED",
                    "lot": None if result is None else f"SYN-BAL-LOT-{assay_sequence:03d}",
                    "quality_status": "unknown" if result is None else "pending_review",
                }
            )
        serums.append({"serum_id": serum_id, "collected_at": _iso(collected_at), "assays": assays})
    return serums, serum_sequence, assay_sequence


def generate_balanced_source_cases(seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """Return 100 cases with explicit test-coverage quotas.

    Quotas are synthetic coverage choices, not estimates of clinical frequency.
    `simulation_scenario` is provenance metadata and must never be used as a
    model feature.
    """

    scenario_types = [
        scenario_type
        for scenario_type, quota in SCENARIO_QUOTAS.items()
        for _ in range(quota)
    ]
    rng = random.Random(seed)
    rng.shuffle(scenario_types)
    cases = generate_source_cases(len(scenario_types), seed=seed)
    serum_sequence = 500
    assay_sequence = 500

    for case_index, (source, scenario_type) in enumerate(zip(cases, scenario_types)):
        phase = "pre_transplant" if case_index % 2 == 0 else "post_transplant"
        source["phase"] = phase
        source["patient_profile"]["rejection_suspicion"] = (
            {"availability": "not_applicable", "value": None, "observed_at": None}
            if phase == "pre_transplant"
            else {"availability": "known", "value": False, "observed_at": "2026-10-15T09:00:00Z"}
        )
        source["patient_profile"]["organ_context"]["status"] = (
            "waiting_list" if phase == "pre_transplant" else "follow_up"
        )
        _set_profile_scenario(source["patient_profile"], scenario_type)
        serums, serum_sequence, assay_sequence = _build_serums(
            scenario_type,
            serum_sequence,
            assay_sequence,
        )
        source["serums"] = serums
        source["provenance"] = {
            "source_record_copied": False,
            "generator_version": "balanced-generator-v1",
            "simulation_scenario": scenario_type,
        }
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = generate_balanced_source_cases(seed=args.seed)
    write_jsonl(cases, args.output)
    print(f"Generated {len(cases)} balanced synthetic source cases in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
