"""Ingestion du CSV synthétique dans la table `patients`.

    uv run python -m app.patients.seed [--csv CHEMIN]      (depuis web/backend/)

Seules l'identité (id, date de naissance, genre) est lue dans le CSV ; le reste est clinique et
n'entre pas dans cette table. Prénom, nom, ville et pays sont fictifs et déterministes.
Le seed est rejouable : un patient déjà présent n'est pas dupliqué. L'ingestion est atomique
(une seule transaction) et n'affiche jamais le contenu du fichier.
"""

import argparse
import asyncio
import csv
import random
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date
from itertools import batched
from pathlib import Path

from app.constants.patients import (
    CSV_COLUMN_BIRTH,
    CSV_COLUMN_GENDER,
    CSV_COLUMN_PATIENT_ID,
    CSV_REQUIRED_COLUMNS,
    DEFAULT_PATIENTS_CSV_PATH,
    SEED_BATCH_SIZE,
    SEED_CITIES,
    SEED_FEMALE_FIRSTNAMES,
    SEED_LASTNAMES,
    SEED_MALE_FIRSTNAMES,
    SEED_UUID_NAMESPACE,
    Gender,
)
from app.core.database import async_session_maker, engine
from app.patients.entity import Patient
from app.patients.exceptions import PatientSeedError
from app.patients.repository import PatientRepository

# Ligne 1 du fichier = en-tête : les données commencent à la ligne 2.
FIRST_DATA_LINE = 2


@dataclass(frozen=True)
class SeedReport:
    read: int
    inserted: int

    @property
    def already_present(self) -> int:
        return self.read - self.inserted


def build_patient_values(row: Mapping[str, str], line: int) -> dict[str, object]:
    """Une ligne du CSV → les valeurs d'une ligne `patients`. `line` ne sert qu'aux erreurs."""
    patient_id = (row[CSV_COLUMN_PATIENT_ID] or "").strip()
    if not patient_id:
        raise PatientSeedError(f"ligne {line} : identifiant patient vide")

    try:
        gender = Gender(row[CSV_COLUMN_GENDER])
    except ValueError:
        raise PatientSeedError(f"ligne {line} : genre inconnu") from None

    raw_birth = (row[CSV_COLUMN_BIRTH] or "").strip()
    try:
        birth = date.fromisoformat(raw_birth) if raw_birth else None
    except ValueError:
        raise PatientSeedError(f"ligne {line} : date de naissance invalide") from None

    # Graine = l'identifiant du CSV : mêmes valeurs à chaque exécution, sur toute machine.
    rng = random.Random(patient_id)
    firstnames = SEED_MALE_FIRSTNAMES if gender is Gender.MALE else SEED_FEMALE_FIRSTNAMES
    city, country = rng.choice(SEED_CITIES)

    return {
        "id": uuid.uuid5(SEED_UUID_NAMESPACE, patient_id),
        "firstname": rng.choice(firstnames),
        "lastname": rng.choice(SEED_LASTNAMES),
        "birth": birth,
        "gender": gender,
        "city": city,
        "country": country,
    }


def read_patient_values(csv_path: Path) -> Iterator[dict[str, object]]:
    """Lit le CSV ligne à ligne (51 000 lignes, très larges : jamais tout en mémoire)."""
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        missing = CSV_REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise PatientSeedError(f"colonnes absentes du CSV : {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=FIRST_DATA_LINE):
            yield build_patient_values(row, line)


async def seed_patients(repository: PatientRepository, csv_path: Path) -> SeedReport:
    read = inserted = 0
    for batch in batched(read_patient_values(csv_path), SEED_BATCH_SIZE):
        inserted += await repository.add_many_ignoring_existing(batch)
        read += len(batch)
    return SeedReport(read=read, inserted=inserted)


async def main(csv_path: Path) -> SeedReport:
    try:
        # Même idée que le `lifespan` : la table est créée si elle manque (pas de migrations).
        async with engine.begin() as connection:
            await connection.run_sync(Patient.__table__.create, checkfirst=True)
        # Une seule transaction : tout ou rien, un CSV invalide en cours de route n'insère rien.
        async with async_session_maker() as session, session.begin():
            return await seed_patients(PatientRepository(session), csv_path)
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingère le CSV de patients synthétiques.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_PATIENTS_CSV_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    report = asyncio.run(main(parse_args().csv))
    print(
        f"{report.read} lignes lues : {report.inserted} patients insérés, "
        f"{report.already_present} déjà présents."
    )
