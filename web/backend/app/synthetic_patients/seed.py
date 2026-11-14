"""Ingestion des patients synthétiques depuis le CSV (table `patients_synthetiques`).

Étape 2 du seed (`python -m app.seed`) : elle part des patients déjà créés par l'étape 1. Pour
chaque ligne du CSV, l'id du patient se déduit du `patient_id` (`patient_id_for`) ; le service
`patients` dit lesquels existent, et seuls ceux-là reçoivent leur patient synthétique. Une ligne
sans patient est comptée, pas insérée (la clé étrangère l'aurait refusée).

Toutes les colonnes du CSV sont reprises, avec la conversion de leur type. Une colonne du CSV
inconnue de la table est ignorée ; une colonne attendue mais absente fait échouer le seed. Le
message d'une erreur ne contient jamais le contenu du fichier.
"""

import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import batched
from pathlib import Path

from sqlalchemy import Column

from app.constants.seed import CSV_COLUMN_PATIENT_ID, SEED_BATCH_SIZE
from app.constants.synthetic_patients import (
    CSV_COLUMN_ALIASES,
    SEED_SYNTHETIC_UUID_NAMESPACE,
    SYNTHETIC_CODE_COLUMN,
    SYNTHETIC_NON_CSV_COLUMNS,
)
from app.core.exceptions import SeedError
from app.core.seed import read_csv_rows
from app.patients.seed import patient_id_for
from app.patients.services import PatientService
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.repository import SyntheticPatientRepository

BOOLEAN_LITERALS = {"true": True, "false": False}

# Colonnes de `patients_synthetiques` qui viennent du CSV. C'est l'entité qui décide : ajouter
# une colonne à l'entité l'ajoute au seed, avec la conversion de son type.
SYNTHETIC_CSV_COLUMNS: dict[str, Column] = {
    column.name: column
    for column in SyntheticPatient.__table__.columns
    if column.name not in SYNTHETIC_NON_CSV_COLUMNS
}


@dataclass(frozen=True)
class SyntheticSeedReport:
    read: int
    inserted: int
    without_patient: int  # lignes dont le patient n'existe pas : non insérées


def column_name_for(csv_header: str) -> str:
    """Nom de colonne en base d'un en-tête du CSV (`hla_A` → `hla_a`, `patient_id` → code)."""
    return CSV_COLUMN_ALIASES.get(csv_header, csv_header.lower())


def convert(column: Column, raw: str, line: int) -> object:
    """Texte du CSV → valeur Python du type de la colonne. Vide = NULL si la colonne l'autorise."""
    if raw == "":
        if column.nullable:
            return None
        raise SeedError(f"ligne {line} : colonne {column.name} vide")
    python_type = column.type.python_type
    try:
        if python_type is bool:
            return BOOLEAN_LITERALS[raw]
        if python_type is date:
            return date.fromisoformat(raw)
        return python_type(raw)  # str, int, float, Gender
    except (ValueError, KeyError):
        # Jamais la valeur du fichier dans le message : seulement où et quelle colonne.
        raise SeedError(f"ligne {line} : colonne {column.name} invalide") from None


def build_synthetic_values(row: Mapping[str, str | None], line: int) -> dict[str, object]:
    """Une ligne du CSV → les valeurs d'une ligne `patients_synthetiques`, rattachée à son patient."""
    values: dict[str, object] = {}
    for header, raw in row.items():
        column = SYNTHETIC_CSV_COLUMNS.get(column_name_for(header)) if header else None
        if column is not None:  # sinon : colonne du CSV inconnue de la table, ignorée
            values[column.name] = convert(column, raw or "", line)
    code = str(values[SYNTHETIC_CODE_COLUMN])
    values["patient_id"] = patient_id_for(code)
    values["id"] = uuid.uuid5(SEED_SYNTHETIC_UUID_NAMESPACE, code)
    return values


def _check_headers(headers: Sequence[str]) -> None:
    present = {column_name_for(header) for header in headers}
    missing = set(SYNTHETIC_CSV_COLUMNS) - present
    if missing:
        raise SeedError(f"colonnes absentes du CSV : {', '.join(sorted(missing))}")


def read_synthetic_values(csv_path: Path) -> Iterator[dict[str, object]]:
    for line, row in read_csv_rows(csv_path, _check_headers):
        yield build_synthetic_values(row, line)


async def seed_synthetic_patients(
    repository: SyntheticPatientRepository, patients: PatientService, csv_path: Path
) -> SyntheticSeedReport:
    read = inserted = without_patient = 0
    for batch in batched(read_synthetic_values(csv_path), SEED_BATCH_SIZE):
        existing = await patients.existing_ids({values["patient_id"] for values in batch})
        attachable = [values for values in batch if values["patient_id"] in existing]
        if attachable:
            inserted += await repository.add_many_ignoring_existing(attachable)
        without_patient += len(batch) - len(attachable)
        read += len(batch)
    return SyntheticSeedReport(read=read, inserted=inserted, without_patient=without_patient)
