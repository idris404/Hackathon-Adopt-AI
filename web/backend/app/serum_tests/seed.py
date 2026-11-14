"""Ingestion de l'historique sérique (table `serum_tests`).

Étape 3 du seed (`python -m app.seed`) : elle part des patients déjà créés. Chaque ligne de
`serum_test_history.csv` est liée par son `patient_id` (« HIS-00355 ») à `patients.patient_id`.
Une ligne dont le patient n'existe pas est comptée, pas insérée. Rejouable : l'`id` est déduit
du couple (`patient_id`, `test_date`). Le message d'une erreur ne contient jamais le contenu
du fichier.
"""

import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import batched
from pathlib import Path

from sqlalchemy import Column

from app.constants.seed import CSV_COLUMN_PATIENT_ID, SEED_BATCH_SIZE
from app.constants.serum_tests import SEED_SERUM_UUID_NAMESPACE, SERUM_NON_CSV_COLUMNS
from app.core.exceptions import SeedError
from app.core.seed import read_csv_rows
from app.patients.services import PatientService
from app.serum_tests.entity import SerumTest
from app.serum_tests.repository import SerumTestRepository

SERUM_CSV_COLUMNS: dict[str, Column] = {
    column.name: column
    for column in SerumTest.__table__.columns
    if column.name not in SERUM_NON_CSV_COLUMNS
}


@dataclass(frozen=True)
class SerumSeedReport:
    read: int
    inserted: int
    without_patient: int


def column_name_for(csv_header: str) -> str:
    """Nom de colonne en base d'un en-tête du CSV (`B12` → `b12`)."""
    return csv_header.lower()


def serum_test_uuid_for(patient_id: str, test_date: date) -> uuid.UUID:
    return uuid.uuid5(SEED_SERUM_UUID_NAMESPACE, f"{patient_id}|{test_date.isoformat()}")


def convert(column: Column, raw: str, line: int) -> object:
    if raw == "":
        if column.nullable:
            return None
        raise SeedError(f"ligne {line} : colonne {column.name} vide")
    python_type = column.type.python_type
    try:
        if python_type is date:
            return date.fromisoformat(raw)
        return python_type(raw)
    except (ValueError, KeyError):
        raise SeedError(f"ligne {line} : colonne {column.name} invalide") from None


def build_serum_values(row: Mapping[str, str | None], line: int) -> dict[str, object]:
    values: dict[str, object] = {}
    for header, raw in row.items():
        column = SERUM_CSV_COLUMNS.get(column_name_for(header)) if header else None
        if column is not None:
            values[column.name] = convert(column, raw or "", line)
    missing = set(SERUM_CSV_COLUMNS) - set(values)
    if missing:
        raise SeedError(f"ligne {line} : colonnes absentes : {', '.join(sorted(missing))}")
    patient_id = str(values[CSV_COLUMN_PATIENT_ID])
    test_date = values["test_date"]
    if not isinstance(test_date, date):
        raise SeedError(f"ligne {line} : colonne test_date invalide")
    values["id"] = serum_test_uuid_for(patient_id, test_date)
    return values


def _check_headers(headers: Sequence[str]) -> None:
    present = {column_name_for(header) for header in headers}
    missing = set(SERUM_CSV_COLUMNS) - present
    if missing:
        raise SeedError(f"colonnes absentes du CSV : {', '.join(sorted(missing))}")


def read_serum_values(csv_path: Path) -> Iterator[dict[str, object]]:
    for line, row in read_csv_rows(csv_path, _check_headers):
        yield build_serum_values(row, line)


async def seed_serum_tests(
    repository: SerumTestRepository, patients: PatientService, csv_path: Path
) -> SerumSeedReport:
    read = inserted = without_patient = 0
    for batch in batched(read_serum_values(csv_path), SEED_BATCH_SIZE):
        existing = await patients.existing_patient_ids(
            {str(values["patient_id"]) for values in batch}
        )
        attachable = [values for values in batch if values["patient_id"] in existing]
        if attachable:
            inserted += await repository.add_many_ignoring_existing(attachable)
        without_patient += len(batch) - len(attachable)
        read += len(batch)
    return SerumSeedReport(read=read, inserted=inserted, without_patient=without_patient)
