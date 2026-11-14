from pathlib import Path

import pytest

from app.conftest import (
    FakePatientRepository,
    FakeSyntheticPatientRepository,
    fake_seed_rows,
    write_seed_csv,
)
from app.constants.seed import SeedStage
from app.patients.seed import PatientSeedReport, patient_id_for
from app.seed import SeedReport, describe, run_seed
from app.synthetic_patients.seed import SyntheticSeedReport

pytestmark = pytest.mark.anyio

ROWS = 4


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(ROWS))


@pytest.fixture
def patients() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def synthetic() -> FakeSyntheticPatientRepository:
    return FakeSyntheticPatientRepository()


async def test_the_full_seed_creates_the_patients_then_their_synthetic_patients(
    csv_path: Path, patients: FakePatientRepository, synthetic: FakeSyntheticPatientRepository
) -> None:
    report = await run_seed(csv_path, patients, synthetic)

    assert report.patients == PatientSeedReport(read=ROWS, inserted=ROWS)
    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=ROWS, without_patient=0
    )
    # Chaque patient synthétique pointe vers un patient créé par la première étape.
    assert {v["patient_id"] for v in synthetic.stored.values()} == set(patients.stored)


async def test_only_patients_leaves_the_synthetic_patients_alone(
    csv_path: Path, patients: FakePatientRepository, synthetic: FakeSyntheticPatientRepository
) -> None:
    report = await run_seed(csv_path, patients, synthetic, SeedStage.PATIENTS)

    assert report.synthetic_patients is None
    assert len(patients.stored) == ROWS
    assert synthetic.stored == {}


async def test_only_synthetic_starts_from_the_patients_already_there(
    csv_path: Path, patients: FakePatientRepository, synthetic: FakeSyntheticPatientRepository
) -> None:
    await run_seed(csv_path, patients, synthetic, SeedStage.PATIENTS)

    report = await run_seed(csv_path, patients, synthetic, SeedStage.SYNTHETIC_PATIENTS)

    assert report.patients is None
    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=ROWS, without_patient=0
    )


async def test_only_synthetic_without_patients_inserts_nothing(
    csv_path: Path, patients: FakePatientRepository, synthetic: FakeSyntheticPatientRepository
) -> None:
    report = await run_seed(csv_path, patients, synthetic, SeedStage.SYNTHETIC_PATIENTS)

    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=0, without_patient=ROWS
    )
    assert patients.stored == {} and synthetic.stored == {}


async def test_replaying_the_full_seed_changes_nothing(
    csv_path: Path, patients: FakePatientRepository, synthetic: FakeSyntheticPatientRepository
) -> None:
    await run_seed(csv_path, patients, synthetic)

    second = await run_seed(csv_path, patients, synthetic)

    assert second.patients == PatientSeedReport(read=ROWS, inserted=0)
    assert second.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=0, without_patient=0
    )
    assert patient_id_for("P-0") in patients.stored
    assert len(synthetic.stored) == ROWS


def test_the_report_tells_what_was_inserted_what_was_there_and_what_was_skipped() -> None:
    report = SeedReport(
        PatientSeedReport(read=10, inserted=4),
        SyntheticSeedReport(read=10, inserted=3, without_patient=2),
    )

    patients_line, synthetic_line = describe(report)

    assert "10 lignes lues, 4 insérés, 6 déjà présents" in patients_line
    assert "10 lignes lues, 3 insérés, 5 déjà présents, 2 sans patient" in synthetic_line


def test_a_stage_that_did_not_run_is_not_reported() -> None:
    assert len(describe(SeedReport(PatientSeedReport(read=1, inserted=1), None))) == 1
    assert describe(SeedReport(None, None)) == []
