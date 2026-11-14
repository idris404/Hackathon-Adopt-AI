"""Ingestion de l'identité des patients depuis le CSV synthétique (table `patients`).

Étape 1 du seed (`python -m app.seed`) : les patients synthétiques (contexte `synthetic_patients`)
partent des patients créés ici, qu'ils retrouvent par leur `patient_id`. Seules `patient_id`,
`date_naissance` et `sexe` viennent du CSV : prénom, nom, ville et pays n'y existent pas, ils sont
fictifs et déterministes. Le message d'une erreur ne contient jamais le contenu du fichier.
"""

import random
import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import batched
from pathlib import Path

from app.constants.patients import (
    CSV_COLUMN_BIRTH,
    CSV_COLUMN_GENDER,
    SEED_CITIES,
    SEED_FEMALE_FIRSTNAMES,
    SEED_LASTNAMES,
    SEED_MALE_FIRSTNAMES,
    SEED_UUID_NAMESPACE,
    Gender,
)
from app.constants.seed import CSV_COLUMN_PATIENT_ID, SEED_BATCH_SIZE
from app.core.exceptions import SeedError
from app.core.seed import read_csv_rows
from app.patients.repository import PatientRepository

REQUIRED_CSV_COLUMNS = frozenset({CSV_COLUMN_PATIENT_ID, CSV_COLUMN_BIRTH, CSV_COLUMN_GENDER})


@dataclass(frozen=True)
class PatientSeedReport:
    read: int
    inserted: int


def patient_uuid_for(code: str) -> uuid.UUID:
    """La clé primaire (`id`) du patient d'une ligne du CSV, déduite de son `patient_id`.

    Même `patient_id` → même `id`, à chaque exécution et après un `--reset` : les URL
    `/patients/{id}` restent valables.
    """
    return uuid.uuid5(SEED_UUID_NAMESPACE, code)


def build_patient_values(row: Mapping[str, str | None], line: int) -> dict[str, object]:
    """Une ligne du CSV → les valeurs d'une ligne `patients`. `line` ne sert qu'aux erreurs."""
    # Pas de `strip()` sur la valeur : le seed des patients synthétiques lit le même `patient_id`
    # tel quel, les deux doivent se retrouver.
    code = row[CSV_COLUMN_PATIENT_ID] or ""
    if not code.strip():
        raise SeedError(f"ligne {line} : identifiant patient vide")

    try:
        gender = Gender(row[CSV_COLUMN_GENDER])
    except ValueError:
        raise SeedError(f"ligne {line} : genre inconnu") from None

    raw_birth = (row[CSV_COLUMN_BIRTH] or "").strip()
    try:
        birth = date.fromisoformat(raw_birth) if raw_birth else None
    except ValueError:
        raise SeedError(f"ligne {line} : date de naissance invalide") from None

    # Graine = l'identifiant du CSV : mêmes valeurs à chaque exécution, sur toute machine.
    rng = random.Random(code)
    firstnames = SEED_MALE_FIRSTNAMES if gender is Gender.MALE else SEED_FEMALE_FIRSTNAMES
    city, country = rng.choice(SEED_CITIES)

    return {
        "id": patient_uuid_for(code),
        "patient_id": code,
        "firstname": rng.choice(firstnames),
        "lastname": rng.choice(SEED_LASTNAMES),
        "birth": birth,
        "gender": gender,
        "city": city,
        "country": country,
    }


def _check_headers(headers: Sequence[str]) -> None:
    missing = REQUIRED_CSV_COLUMNS - set(headers)
    if missing:
        raise SeedError(f"colonnes absentes du CSV : {', '.join(sorted(missing))}")


def read_patient_values(csv_path: Path) -> Iterator[dict[str, object]]:
    for line, row in read_csv_rows(csv_path, _check_headers):
        yield build_patient_values(row, line)


async def seed_patients(repository: PatientRepository, csv_path: Path) -> PatientSeedReport:
    read = inserted = 0
    for batch in batched(read_patient_values(csv_path), SEED_BATCH_SIZE):
        inserted += await repository.add_many_ignoring_existing(batch)
        read += len(batch)
    return PatientSeedReport(read=read, inserted=inserted)
