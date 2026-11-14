"""Seed de la base : patients, patients synthétiques, historique sérique, événements, puis le
compte de démonstration.

    uv run python -m app.seed [--csv CHEMIN] [--serum-csv CHEMIN]
        [--only patients|synthetic|serum|history|users] [--reset]
                                                                      (depuis web/backend/)

Les patients synthétiques, les tests sériques et l'historique d'événements partent des patients
(liés par `patient_id`, ex. « HIS-00355 ») : l'étape `patients` passe d'abord. `--only synthetic`,
`--only serum` ou `--only history` ne relance que cette étape, à condition que les patients
existent déjà. Rejouable : ce qui est déjà présent n'est pas dupliqué. Une seule transaction :
tout ou rien.

L'étape `users` crée le compte de démonstration (développement local uniquement) : email et mot de
passe lus dans web/.env (`SEED_USER_EMAIL`, `SEED_USER_PASSWORD`), le seed s'arrête avant de toucher à
la base s'ils manquent ou sont invalides. Elle passe en dernier et dans sa propre session : l'adaptateur FastAPI Users valide
lui-même (`commit`), ce qui ne peut pas se faire dans la transaction des CSV. Si un CSV est invalide,
l'étape n'est jamais atteinte et aucun compte n'est créé. `--reset` ne touche pas à la table `user`.

Il n'y a pas d'outil de migration : si le schéma d'une table a changé depuis sa création, le seed
refuse de continuer. `--reset` supprime alors les quatre tables et les recrée (leurs données se
régénèrent depuis les CSV et les événements fictifs ; les identifiants `id` sont les mêmes qu'avant).
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import Connection, Table, inspect

from app.constants.seed import (
    DEFAULT_PATIENTS_CSV_PATH,
    DEFAULT_SERUM_HISTORY_CSV_PATH,
    SeedStage,
)
from app.core.database import Base, async_session_maker, engine
from app.core.exceptions import SeedError
from app.core.security import build_password_helper
from app.patient_history.entity import PatientHistory
from app.patient_history.repository import PatientHistoryRepository
from app.patient_history.seed import HistorySeedReport, seed_patient_history
from app.patients.entity import Patient
from app.patients.repository import PatientRepository
from app.patients.seed import PatientSeedReport, seed_patients
from app.patients.services import PatientService
from app.serum_tests.entity import SerumTest
from app.serum_tests.repository import SerumTestRepository
from app.serum_tests.seed import SerumSeedReport, seed_serum_tests
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.repository import SyntheticPatientRepository
from app.synthetic_patients.seed import SyntheticSeedReport, seed_synthetic_patients
from app.users.entity import User
from app.users.seed import DemoUser, UserSeedReport, load_demo_user, seed_users
from app.users.services import UserManager

# Ordre de création (les patients d'abord : les clés étrangères pointent vers eux).
TABLES: Sequence[Table] = (
    Patient.__table__,
    SyntheticPatient.__table__,
    SerumTest.__table__,
    PatientHistory.__table__,
)

# Créée si absente, mais jamais supprimée par `--reset` : elle porte les comptes et leurs sessions.
USER_TABLES: Sequence[Table] = (User.__table__,)


@dataclass(frozen=True)
class SeedReport:
    patients: PatientSeedReport | None  # None : étape non exécutée
    synthetic_patients: SyntheticSeedReport | None
    serum_tests: SerumSeedReport | None = None
    patient_history: HistorySeedReport | None = None
    users: UserSeedReport | None = None


async def run_seed(
    csv_path: Path,
    patient_repository: PatientRepository,
    synthetic_repository: SyntheticPatientRepository,
    serum_repository: SerumTestRepository,
    history_repository: PatientHistoryRepository,
    only: SeedStage | None = None,
    serum_csv_path: Path | None = None,
    user_manager: UserManager | None = None,
    demo_user: DemoUser | None = None,
) -> SeedReport:
    patients_report = synthetic_report = serum_report = history_report = users_report = None
    patients = PatientService(patient_repository)
    if only in (None, SeedStage.PATIENTS):
        patients_report = await seed_patients(patient_repository, csv_path)
    if only in (None, SeedStage.SYNTHETIC_PATIENTS):
        synthetic_report = await seed_synthetic_patients(synthetic_repository, patients, csv_path)
    if only in (None, SeedStage.SERUM_TESTS):
        if serum_csv_path is None:
            raise SeedError("chemin du CSV d'historique sérique manquant")
        serum_report = await seed_serum_tests(serum_repository, patients, serum_csv_path)
    if only in (None, SeedStage.PATIENT_HISTORY):
        history_report = await seed_patient_history(history_repository, patients)
    if only in (None, SeedStage.USERS):
        if user_manager is None or demo_user is None:
            raise SeedError("gestionnaire d'utilisateurs ou compte de démonstration manquant")
        users_report = await seed_users(user_manager, demo_user)
    return SeedReport(patients_report, synthetic_report, serum_report, history_report, users_report)


def find_outdated_tables(connection: Connection) -> list[str]:
    """Les tables existantes dont les colonnes ne sont plus celles de l'entité."""
    inspector = inspect(connection)
    outdated = []
    for table in TABLES:
        if inspector.has_table(table.name):
            existing = {column["name"] for column in inspector.get_columns(table.name)}
            if existing != {column.name for column in table.columns}:
                outdated.append(table.name)
    return outdated


async def prepare_tables(reset: bool) -> None:
    """Crée les tables manquantes (comme le `lifespan`), ou les recrée si `reset`."""
    async with engine.begin() as connection:
        if reset:
            await connection.run_sync(Base.metadata.drop_all, tables=TABLES)
        outdated = await connection.run_sync(find_outdated_tables)
        if outdated:
            raise SeedError(
                f"schéma obsolète pour {', '.join(outdated)} : relancer avec --reset "
                "(recrée les tables patients, patients_synthetiques, serum_tests et "
                "patient_history ; leurs données se régénèrent depuis les CSV et les "
                "événements fictifs)"
            )
        await connection.run_sync(Base.metadata.create_all, tables=(*TABLES, *USER_TABLES))


async def main(
    csv_path: Path,
    serum_csv_path: Path,
    only: SeedStage | None = None,
    reset: bool = False,
) -> SeedReport:
    try:
        # Avant tout travail : un .env incomplet ne doit pas coûter la lecture de 51 000 lignes.
        demo_user = load_demo_user() if only in (None, SeedStage.USERS) else None
        await prepare_tables(reset)
        # Session à part pour les utilisateurs : l'adaptateur FastAPI Users fait son propre `commit`.
        async with async_session_maker() as user_session:
            user_manager = UserManager(
                SQLAlchemyUserDatabase(user_session, User), build_password_helper()
            )
            # Une seule transaction : tout ou rien, un CSV invalide en cours de route n'insère rien.
            async with async_session_maker() as session, session.begin():
                return await run_seed(
                    csv_path,
                    PatientRepository(session),
                    SyntheticPatientRepository(session),
                    SerumTestRepository(session),
                    PatientHistoryRepository(session),
                    only,
                    serum_csv_path,
                    user_manager,
                    demo_user,
                )
    finally:
        await engine.dispose()


def describe(report: SeedReport) -> list[str]:
    lines = []
    if report.patients:
        read, inserted = report.patients.read, report.patients.inserted
        lines.append(
            f"patients : {read} lignes lues, {inserted} insérés, {read - inserted} déjà présents"
        )
    if report.synthetic_patients:
        synthetic = report.synthetic_patients
        already = synthetic.read - synthetic.without_patient - synthetic.inserted
        lines.append(
            f"patients synthétiques : {synthetic.read} lignes lues, {synthetic.inserted} insérés, "
            f"{already} déjà présents, {synthetic.without_patient} sans patient (ignorés)"
        )
    if report.serum_tests:
        serum = report.serum_tests
        already = serum.read - serum.without_patient - serum.inserted
        lines.append(
            f"tests sériques : {serum.read} lignes lues, {serum.inserted} insérés, "
            f"{already} déjà présents, {serum.without_patient} sans patient (ignorés)"
        )
    if report.patient_history:
        history = report.patient_history
        already = history.read - history.without_patient - history.inserted
        lines.append(
            f"historique : {history.read} événements, {history.inserted} insérés, "
            f"{already} déjà présents, {history.without_patient} sans patient (ignorés)"
        )
    if report.users:
        lines.append(
            "compte de démonstration : "
            + ("créé" if report.users.created else "déjà présent, inchangé")
        )
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingère les CSV patients, synthétiques et sériques, l'historique fictif, "
            "puis le compte de démonstration."
        )
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_PATIENTS_CSV_PATH)
    parser.add_argument("--serum-csv", type=Path, default=DEFAULT_SERUM_HISTORY_CSV_PATH)
    parser.add_argument("--only", type=SeedStage, choices=list(SeedStage), default=None)
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "supprime et recrée patients, patients_synthetiques, serum_tests et "
            "patient_history avant le seed"
        ),
    )
    args = parser.parse_args()
    if args.reset and args.only:
        parser.error("--reset recrée les quatre tables : incompatible avec --only")
    return args


if __name__ == "__main__":
    args = parse_args()
    try:
        report = asyncio.run(main(args.csv, args.serum_csv, args.only, args.reset))
    except SeedError as error:
        sys.exit(f"erreur : {error}")
    if args.reset:
        print("tables patients, patients_synthetiques, serum_tests et patient_history recréées")
    print("\n".join(describe(report)))
