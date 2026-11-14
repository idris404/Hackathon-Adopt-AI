"""Seed de la base : peuple `patients` puis `patients_synthetiques` depuis le CSV synthétique.

    uv run python -m app.seed [--csv CHEMIN] [--only patients|synthetic]      (depuis web/backend/)

Les patients synthétiques partent des patients : l'étape `patients` passe d'abord. `--only
synthetic` ne relance que la seconde, à condition que les patients existent déjà.
Rejouable : ce qui est déjà présent n'est pas dupliqué. Une seule transaction : tout ou rien.
"""

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.constants.seed import DEFAULT_PATIENTS_CSV_PATH, SeedStage
from app.core.database import Base, async_session_maker, engine
from app.patients.entity import Patient
from app.patients.repository import PatientRepository
from app.patients.seed import PatientSeedReport, seed_patients
from app.patients.services import PatientService
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.repository import SyntheticPatientRepository
from app.synthetic_patients.seed import SyntheticSeedReport, seed_synthetic_patients


@dataclass(frozen=True)
class SeedReport:
    patients: PatientSeedReport | None  # None : étape non exécutée
    synthetic_patients: SyntheticSeedReport | None


async def run_seed(
    csv_path: Path,
    patient_repository: PatientRepository,
    synthetic_repository: SyntheticPatientRepository,
    only: SeedStage | None = None,
) -> SeedReport:
    patients_report = synthetic_report = None
    if only in (None, SeedStage.PATIENTS):
        patients_report = await seed_patients(patient_repository, csv_path)
    if only in (None, SeedStage.SYNTHETIC_PATIENTS):
        synthetic_report = await seed_synthetic_patients(
            synthetic_repository, PatientService(patient_repository), csv_path
        )
    return SeedReport(patients_report, synthetic_report)


async def main(csv_path: Path, only: SeedStage | None = None) -> SeedReport:
    try:
        # Même idée que le `lifespan` : les tables sont créées si elles manquent (pas de migrations).
        tables = [Patient.__table__, SyntheticPatient.__table__]
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all, tables=tables)
        # Une seule transaction : tout ou rien, un CSV invalide en cours de route n'insère rien.
        async with async_session_maker() as session, session.begin():
            return await run_seed(
                csv_path, PatientRepository(session), SyntheticPatientRepository(session), only
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
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingère le CSV de patients synthétiques.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_PATIENTS_CSV_PATH)
    parser.add_argument("--only", type=SeedStage, choices=list(SeedStage), default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print("\n".join(describe(asyncio.run(main(args.csv, args.only)))))
