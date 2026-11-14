"""Import the large synthetic profile dataset without applying pending scores."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, TextIO

from .profile_csv_importer import CSV_COLUMNS, ProfileImportError, _source_case
from .validator import validate_source_case


IMPORTER_VERSION = "profile-csv-importer-v2"
SOURCE_DATASET = "patients_synthetiques-v2"
OUTCOME_COLUMNS = ("issue_statut", "rejet_1an", "type_rejet", "date_rejet")
GENERATION_TRUTH_COLUMNS = (
    "_verite_groupe",
    "_verite_tgi",
    "_verite_interdits",
    "_verite_dsa",
    "_verite_mfi_dsa_max",
    "_verite_p_rejet",
    "_verite_p_rejet_donneur_quelconque",
)
V2_EXTRA_COLUMNS = (
    "jeu",
    "maladie_renale_initiale",
    "type_donneur",
    *OUTCOME_COLUMNS,
    *GENERATION_TRUTH_COLUMNS,
)
V2_REQUIRED_COLUMNS = tuple(
    column for column in CSV_COLUMNS if column not in {"niveau_risque", "niveau_risque_statut", "niveau_risque_justification"}
) + V2_EXTRA_COLUMNS


def _open_csv(path: Path, stack: ExitStack) -> TextIO:
    if path.suffix == ".gz":
        return stack.enter_context(gzip.open(path, mode="rt", encoding="utf-8-sig", newline=""))
    return stack.enter_context(path.open(mode="r", encoding="utf-8-sig", newline=""))


def _decoded_input_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return gzip.decompress(raw) if path.suffix == ".gz" else raw


def _open_deterministic_gzip_text(path: Path, stack: ExitStack) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = stack.enter_context(path.open("wb"))
    compressed = stack.enter_context(gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0))
    return stack.enter_context(io.TextIOWrapper(compressed, encoding="utf-8", newline=""))


def _outcome_record(row: dict[str, str], source: dict[str, Any]) -> dict[str, Any]:
    raw_rejection = row["rejet_1an"]
    rejection = True if raw_rejection == "true" else False if raw_rejection == "false" else None
    status = {
        "observee": "observed",
        "en_cours": "ongoing",
        "non_applicable": "not_applicable",
    }[row["issue_statut"]]
    return {
        "case_id": source["case_id"],
        "synthetic": True,
        "phase": source["phase"],
        "outcome_status": status,
        "rejection_within_one_year": rejection,
        "rejection_type": row["type_rejet"] or None,
        "rejection_date": row["date_rejet"] or None,
        "label_status": "simulated_source_outcome",
        "provenance": source["provenance"],
    }


def _validate_outcome(row: dict[str, str]) -> None:
    status = row["issue_statut"]
    rejection = row["rejet_1an"]
    if status not in {"observee", "en_cours", "non_applicable"}:
        raise ProfileImportError(f"{row['patient_id']}: unsupported issue_statut {status}")
    if status == "observee" and rejection not in {"true", "false"}:
        raise ProfileImportError(f"{row['patient_id']}: observed outcome requires rejet_1an")
    if status == "en_cours" and rejection == "false":
        raise ProfileImportError(f"{row['patient_id']}: ongoing follow-up cannot establish rejection absence")
    if status == "non_applicable" and rejection:
        raise ProfileImportError(f"{row['patient_id']}: non-applicable outcome cannot contain rejet_1an")
    if rejection == "true" and (not row["type_rejet"] or not row["date_rejet"]):
        raise ProfileImportError(f"{row['patient_id']}: rejection outcome requires type and date")
    if rejection != "true" and (row["type_rejet"] or row["date_rejet"]):
        raise ProfileImportError(f"{row['patient_id']}: rejection details require rejet_1an=true")


def import_profile_csv_v2(
    input_path: Path,
    sources_path: Path,
    outcomes_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Import kidney-only profile facts and isolate future outcomes as labels."""

    paths = (input_path, sources_path, outcomes_path, report_path)
    if len({path.resolve() for path in paths}) != len(paths):
        raise ProfileImportError("Input and output paths must be distinct")
    if not input_path.is_file():
        raise ProfileImportError(f"CSV file does not exist: {input_path}")
    if sources_path.suffix != ".gz" or outcomes_path.suffix != ".gz":
        raise ProfileImportError("Large v2 JSONL outputs must use the .gz extension")

    input_bytes = _decoded_input_bytes(input_path)
    source_hash = hashlib.sha256()
    outcome_hash = hashlib.sha256()
    excluded = Counter()
    contradictions = Counter()
    partitions = Counter()
    phases = Counter()
    outcome_statuses = Counter()
    rejection_labels = Counter()
    total_records = 0
    imported_records = 0
    seen_patient_ids: set[str] = set()

    with ExitStack() as stack:
        input_handle = _open_csv(input_path, stack)
        reader = csv.DictReader(input_handle)
        missing_columns = sorted(set(V2_REQUIRED_COLUMNS) - set(reader.fieldnames or ()))
        if missing_columns:
            raise ProfileImportError(f"Missing CSV columns: {', '.join(missing_columns)}")
        source_handle = _open_deterministic_gzip_text(sources_path, stack)
        outcome_handle = _open_deterministic_gzip_text(outcomes_path, stack)

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
            _validate_outcome(row)
            outcome = _outcome_record(row, source)

            source_line = f"{json.dumps(source, ensure_ascii=False, sort_keys=True)}\n"
            outcome_line = f"{json.dumps(outcome, ensure_ascii=False, sort_keys=True)}\n"
            source_handle.write(source_line)
            outcome_handle.write(outcome_line)
            source_hash.update(source_line.encode("utf-8"))
            outcome_hash.update(outcome_line.encode("utf-8"))
            contradictions.update(detected)
            partitions[row["jeu"]] += 1
            phases[source["phase"]] += 1
            outcome_statuses[outcome["outcome_status"]] += 1
            rejection_labels[str(outcome["rejection_within_one_year"]).lower()] += 1

    report = {
        "importer_version": IMPORTER_VERSION,
        "source_dataset": SOURCE_DATASET,
        "input_file": input_path.name,
        "input_content_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "total_records": total_records,
        "imported_records": imported_records,
        "excluded_records": sum(excluded.values()),
        "excluded_by_reason": dict(sorted(excluded.items())),
        "detected_contradictions": dict(sorted(contradictions.items())),
        "source_partitions": dict(sorted(partitions.items())),
        "phases": dict(sorted(phases.items())),
        "outcome_statuses": dict(sorted(outcome_statuses.items())),
        "rejection_within_one_year_labels": dict(sorted(rejection_labels.items())),
        "generation_truth_columns_excluded": list(GENERATION_TRUTH_COLUMNS),
        "generation_metadata_columns_excluded": ["_anomalies_injectees"],
        "profile_scoring_status": "pending_healthcare_professional_scoring",
        "profile_scores_generated": False,
        "outputs": {
            "sources": {
                "file": sources_path.name,
                "compression": "gzip",
                "content_sha256": source_hash.hexdigest(),
            },
            "outcomes": {
                "file": outcomes_path.name,
                "compression": "gzip",
                "content_sha256": outcome_hash.hexdigest(),
            },
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(f"{json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = import_profile_csv_v2(args.input, args.sources, args.outcomes, args.report)
    print(
        f"Imported {report['imported_records']} kidney profiles without scoring; "
        f"excluded {report['excluded_records']} unsupported records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
