"""Import the corrected synthetic profile dataset and apply PROFILE-1.0.0."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .profile_analyzer import analyze_profile
from .profile_csv_importer import ProfileImportError, _source_case
from .profile_csv_v2_importer import (
    GENERATION_TRUTH_COLUMNS,
    V2_REQUIRED_COLUMNS,
    _decoded_input_bytes,
    _open_csv,
    _open_deterministic_gzip_text,
    _outcome_record,
    _validate_outcome,
)
from .validator import RULESET_VERSION, validate_source_case


IMPORTER_VERSION = "profile-csv-importer-v3"
SOURCE_DATASET = "patients_synthetiques-v3"
V2_OUTCOME_COLUMNS = ("issue_statut", "rejet_1an", "type_rejet", "date_rejet")
OUTCOME_COLUMNS = ("_issue_statut", "_rejet_1an", "_type_rejet", "_date_rejet")
GENERATION_TRUTH_COLUMNS_V3 = (*GENERATION_TRUTH_COLUMNS, "_verite_risque_reference")
V3_REQUIRED_COLUMNS = tuple(
    column for column in V2_REQUIRED_COLUMNS if column not in V2_OUTCOME_COLUMNS
) + ("antecedent_rejet", *OUTCOME_COLUMNS, "_verite_risque_reference")


def _outcome_row(row: dict[str, str]) -> dict[str, str]:
    normalized = dict(row)
    for old_name, new_name in zip(V2_OUTCOME_COLUMNS, OUTCOME_COLUMNS):
        normalized[old_name] = row[new_name]
    return normalized


def _profile_record(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": source["case_id"],
        "synthetic": True,
        "phase": source["phase"],
        "profile": analyze_profile(source["patient_profile"]),
        "ruleset_version": RULESET_VERSION,
        "human_validation_required": True,
        "provenance": source["provenance"],
    }


def import_profile_csv_v3(
    input_path: Path,
    sources_path: Path,
    profiles_path: Path,
    outcomes_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Import kidney profiles, calculated scores, and isolated future labels."""

    paths = (input_path, sources_path, profiles_path, outcomes_path, report_path)
    if len({path.resolve() for path in paths}) != len(paths):
        raise ProfileImportError("Input and output paths must be distinct")
    if not input_path.is_file():
        raise ProfileImportError(f"CSV file does not exist: {input_path}")
    if any(path.suffix != ".gz" for path in (sources_path, profiles_path, outcomes_path)):
        raise ProfileImportError("Large v3 JSONL outputs must use the .gz extension")

    input_bytes = _decoded_input_bytes(input_path)
    content_hashes = {name: hashlib.sha256() for name in ("sources", "profiles", "outcomes")}
    excluded: Counter[str] = Counter()
    contradictions: Counter[str] = Counter()
    applied_defaults: Counter[str] = Counter()
    partitions: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    score_statuses: Counter[str] = Counter()
    outcome_statuses: Counter[str] = Counter()
    total_records = 0
    imported_records = 0
    seen_patient_ids: set[str] = set()

    with ExitStack() as stack:
        reader = csv.DictReader(_open_csv(input_path, stack))
        missing_columns = sorted(set(V3_REQUIRED_COLUMNS) - set(reader.fieldnames or ()))
        if missing_columns:
            raise ProfileImportError(f"Missing CSV columns: {', '.join(missing_columns)}")
        handles = {
            "sources": _open_deterministic_gzip_text(sources_path, stack),
            "profiles": _open_deterministic_gzip_text(profiles_path, stack),
            "outcomes": _open_deterministic_gzip_text(outcomes_path, stack),
        }

        for row in reader:
            total_records += 1
            patient_id = row["patient_id"]
            if patient_id in seen_patient_ids:
                raise ProfileImportError(f"Duplicate patient_id: {patient_id}")
            seen_patient_ids.add(patient_id)
            if row["synthetic"].lower() != "true":
                raise ProfileImportError(f"{patient_id}: every record must be explicitly synthetic=true")
            if row["organe"] != "Rein":
                excluded[f"unsupported_organ:{row['organe']}"] += 1
                continue

            if row["greffe_anterieure_statut"] == "inconnu":
                applied_defaults["unknown_previous_transplant_as_none"] += 1
            if row["antecedent_rejet"] == "inconnu":
                applied_defaults["unknown_rejection_history_as_none"] += 1

            imported_records += 1
            source, detected = _source_case(row, imported_records)
            source["case_id"] = f"SYN-PROFILE-{imported_records:05d}"
            source["patient_profile"]["source_context"].update(
                {
                    "initial_kidney_disease": row["maladie_renale_initiale"],
                    "donor_type": row["type_donneur"] or None,
                }
            )
            source["provenance"].update(
                {
                    "generator_version": IMPORTER_VERSION,
                    "source_dataset": SOURCE_DATASET,
                    "source_partition": row["jeu"],
                }
            )
            validate_source_case(source)
            normalized_outcome = _outcome_row(row)
            _validate_outcome(normalized_outcome)
            profile = _profile_record(source)
            outcome = _outcome_record(normalized_outcome, source)

            for name, record in (("sources", source), ("profiles", profile), ("outcomes", outcome)):
                line = f"{json.dumps(record, ensure_ascii=False, sort_keys=True)}\n"
                handles[name].write(line)
                content_hashes[name].update(line.encode("utf-8"))

            contradictions.update(detected)
            partitions[row["jeu"]] += 1
            categories[profile["profile"]["proposed_risk_category"]] += 1
            score_statuses[profile["profile"]["score_status"]] += 1
            outcome_statuses[outcome["outcome_status"]] += 1

    output_paths = {"sources": sources_path, "profiles": profiles_path, "outcomes": outcomes_path}
    report = {
        "importer_version": IMPORTER_VERSION,
        "source_dataset": SOURCE_DATASET,
        "ruleset_version": RULESET_VERSION,
        "input_file": input_path.name,
        "input_content_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "total_records": total_records,
        "imported_records": imported_records,
        "excluded_records": sum(excluded.values()),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "detected_contradictions": dict(sorted(contradictions.items())),
        "applied_defaults": dict(sorted(applied_defaults.items())),
        "applied_normalizations": {
            key: contradictions[key]
            for key in (
                "previous_transplant_after_reference_date",
                "transfusion_regular_with_single_event",
            )
            if contradictions[key]
        },
        "unresolved_source_inconsistencies": {
            key: contradictions[key]
            for key in ("dialysis_before_birth", "pregnancy_dates_with_zero_count")
            if contradictions[key]
        },
        "source_partitions": dict(sorted(partitions.items())),
        "profile_categories": dict(sorted(categories.items())),
        "profile_score_statuses": dict(sorted(score_statuses.items())),
        "outcome_statuses": dict(sorted(outcome_statuses.items())),
        "generation_truth_columns_excluded": list(GENERATION_TRUTH_COLUMNS_V3),
        "generation_metadata_columns_excluded": ["_anomalies_injectees"],
        "profile_scores_generated": True,
        "outputs": {
            name: {
                "file": path.name,
                "compression": "gzip",
                "content_sha256": content_hashes[name].hexdigest(),
            }
            for name, path in output_paths.items()
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(f"{json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = import_profile_csv_v3(
        args.input, args.sources, args.profiles, args.outcomes, args.report
    )
    print(
        f"Imported and scored {report['imported_records']} kidney profiles; "
        f"excluded {report['excluded_records']} unsupported records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
