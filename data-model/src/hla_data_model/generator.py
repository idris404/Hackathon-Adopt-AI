"""Generate deterministic synthetic source cases without medical labels."""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_SEED = 20261114
EVALUATION_TIME = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)
RESULT_OPTIONS: tuple[str | None, ...] = ("negative", "positive", "doubtful", None)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _boolean_observation(rng: random.Random) -> dict[str, Any]:
    if rng.random() < 0.1:
        return {"availability": "missing", "value": None}
    return {"availability": "known", "value": rng.choice([False, True])}


def generate_source_cases(count: int, seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """Return reproducible, non-representative source cases.

    These cases provide input variety for UI and contract testing. No medical
    score, risk category, decision, performance label, or expected restitution
    is generated.
    """

    if not 1 <= count <= 250:
        raise ValueError("count must be between 1 and 250")
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    assay_sequence = 100
    serum_sequence = 100

    for case_offset in range(count):
        case_number = 100 + case_offset
        age_value = rng.choice([None, 35, 48, 52, 65, 66, 72])
        pregnancy_count = rng.choice([0, 0, 1, 2])
        pregnancy_status = {0: "none", 1: "one", 2: "multiple"}[pregnancy_count]
        sex_at_birth = "female" if pregnancy_count > 0 else rng.choice(["female", "male", "intersex"])
        transfusion_count = rng.choice([0, 0, 1, 2])
        transfusion_frequency = {0: "none", 1: "single", 2: "multiple"}[transfusion_count]
        phase = rng.choice(["pre_transplant", "post_transplant"])
        dialysis_status = rng.choice(["not_on_dialysis", "on_dialysis"])
        rejection_suspicion = (
            {"availability": "known", "value": rng.choice([False, False, True]), "observed_at": "2026-10-15T09:00:00Z"}
            if phase == "post_transplant"
            else {"availability": "not_applicable", "value": None, "observed_at": None}
        )
        car_t_events = [] if rng.random() < 0.9 else [{"treatment_code": "SYN-CAR-T", "start_date": "2025-04-10"}]
        antibody_events = (
            []
            if rng.random() < 0.85
            else [{"treatment_code": "SYN-THERAPEUTIC-ANTIBODY", "start_date": "2025-06-12"}]
        )
        serum_count = rng.choice([2, 3])
        serums: list[dict[str, Any]] = []

        for serum_offset in range(serum_count):
            collected_at = EVALUATION_TIME - timedelta(
                days=((serum_count - serum_offset) * 45) + (case_offset % 30),
                hours=1,
            )
            result = rng.choice(RESULT_OPTIONS)
            serum_id = f"SER-{serum_sequence:03d}"
            assay_id = f"ASSAY-{assay_sequence:03d}"
            serum_sequence += 1
            assay_sequence += 1
            serums.append(
                {
                    "serum_id": serum_id,
                    "collected_at": _iso(collected_at),
                    "assays": [
                        {
                            "assay_id": assay_id,
                            "test_type": rng.choice(["screening", "single_antigen"]),
                            "manufacturer": "Immucor",
                            "result_availability": "missing" if result is None else "present",
                            "source_result": result,
                            "performed_at": None if result is None else _iso(collected_at + timedelta(hours=4)),
                            "kit_reference": "SYN-IMM-GENERATED",
                            "lot": None if result is None else f"SYN-GEN-LOT-{assay_sequence:03d}",
                            "quality_status": "unknown" if result is None else "pending_review",
                        }
                    ],
                }
            )

        cases.append(
            {
                "case_id": f"SYN-CASE-{case_number:03d}",
                "synthetic": True,
                "schema_version": "0.2.0",
                "phase": phase,
                "evaluation_time": _iso(EVALUATION_TIME),
                "patient_profile": {
                    "age": {"availability": "missing" if age_value is None else "known", "value": age_value},
                    "sex_at_birth": {"availability": "known", "value": sex_at_birth},
                    "pregnancy_history": {
                        "availability": "known",
                        "status": pregnancy_status,
                        "count": pregnancy_count,
                        "dates": [],
                    },
                    "transfusion_history": {
                        "availability": "known",
                        "count": transfusion_count,
                        "dates": [],
                        "frequency": transfusion_frequency,
                    },
                    "diabetes": _boolean_observation(rng),
                    "hypertension": _boolean_observation(rng),
                    "autoimmune_disease": _boolean_observation(rng),
                    "dialysis": {
                        "availability": "known",
                        "status": dialysis_status,
                        "started_at": "2024-01-15" if dialysis_status == "on_dialysis" else None,
                    },
                    "rejection_suspicion": rejection_suspicion,
                    "organ_context": {
                        "availability": "known",
                        "target_organ": "kidney",
                        "status": "waiting_list" if phase == "pre_transplant" else "follow_up",
                        "registration_date": "2023-09-01",
                    },
                    "previous_transplants": {"availability": "known", "events": []},
                    "car_t_treatments": {"availability": "known", "events": car_t_events},
                    "therapeutic_antibody_treatments": {"availability": "known", "events": antibody_events},
                },
                "serums": serums,
                "provenance": {
                    "source_record_copied": False,
                    "generator_version": "deterministic-generator-v1",
                },
            }
        )
    return cases


def write_jsonl(cases: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = generate_source_cases(args.count, args.seed)
    write_jsonl(cases, args.output)
    print(f"Generated {len(cases)} synthetic source cases in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
