import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.conftest import (
    FakePatientHistoryRepository,
    FakePatientRepository,
    FakeSerumTestRepository,
    FakeSyntheticPatientRepository,
    fake_seed_rows,
    write_seed_csv,
)
from app.constants.patient_history import DEMO_PATIENTS, HISTORY_EVENTS
from app.constants.seed import SeedStage
from app.core.database import Base
from app.patient_history.seed import HistorySeedReport
from app.patients.seed import PatientSeedReport, patient_uuid_for
from app.seed import TABLES, SeedReport, describe, find_outdated_tables, parse_args, run_seed
from app.serum_tests.seed import SerumSeedReport
from app.synthetic_patients.seed import SyntheticSeedReport

pytestmark = pytest.mark.anyio

ROWS = 4
HISTORY_ROWS = len(DEMO_PATIENTS) * len(HISTORY_EVENTS)


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(ROWS))


@pytest.fixture
def patients() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def synthetic() -> FakeSyntheticPatientRepository:
    return FakeSyntheticPatientRepository()


@pytest.fixture
def serum() -> FakeSerumTestRepository:
    return FakeSerumTestRepository()


@pytest.fixture
def history() -> FakePatientHistoryRepository:
    return FakePatientHistoryRepository()


def serum_row(patient_id: str, test_date: str = "2017-12-09") -> dict[str, str]:
    return {
        "patient_id": patient_id,
        "graft_date": "2016-08-04",
        "test_date": test_date,
        "B12": "40",
        "B12_output": "0",
        "B13": "190",
        "B13_output": "0",
        "DR53": "291",
        "DR53_output": "0",
        "DR51": "177",
        "DR51_output": "0",
        "DQ10": "1870",
        "DQ10_output": "1",
        "profile": "C",
    }


@pytest.fixture
def serum_csv(tmp_path: Path) -> Path:
    # P-0 existe après l'étape patients ; ABSENT n'a pas de patient.
    return write_seed_csv(
        tmp_path / "serum.csv",
        [serum_row("P-0"), serum_row("ABSENT", test_date="2018-01-01")],
    )


async def test_the_full_seed_creates_the_patients_then_their_synthetic_patients(
    csv_path: Path,
    serum_csv: Path,
    patients: FakePatientRepository,
    synthetic: FakeSyntheticPatientRepository,
    serum: FakeSerumTestRepository,
    history: FakePatientHistoryRepository,
) -> None:
    report = await run_seed(
        csv_path, patients, synthetic, serum, history, serum_csv_path=serum_csv
    )

    assert report.patients == PatientSeedReport(read=ROWS, inserted=ROWS)
    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=ROWS, without_patient=0
    )
    assert report.serum_tests == SerumSeedReport(read=2, inserted=1, without_patient=1)
    assert report.patient_history == HistorySeedReport(
        read=HISTORY_ROWS, inserted=0, without_patient=HISTORY_ROWS
    )
    # Chaque patient synthétique pointe, par `patient_id`, vers un patient créé par la première étape.
    created = {v["patient_id"] for v in patients.stored.values()}
    assert {v["patient_id"] for v in synthetic.stored.values()} == created
    assert {v["patient_id"] for v in serum.stored.values()} == {"P-0"}


async def test_only_patients_leaves_the_synthetic_patients_alone(
    csv_path: Path,
    patients: FakePatientRepository,
    synthetic: FakeSyntheticPatientRepository,
    serum: FakeSerumTestRepository,
    history: FakePatientHistoryRepository,
) -> None:
    report = await run_seed(csv_path, patients, synthetic, serum, history, SeedStage.PATIENTS)

    assert report.synthetic_patients is None
    assert report.serum_tests is None
    assert report.patient_history is None
    assert len(patients.stored) == ROWS
    assert synthetic.stored == {}
    assert serum.stored == {}
    assert history.stored == {}


async def test_only_synthetic_starts_from_the_patients_already_there(
    csv_path: Path,
    patients: FakePatientRepository,
    synthetic: FakeSyntheticPatientRepository,
    serum: FakeSerumTestRepository,
    history: FakePatientHistoryRepository,
) -> None:
    await run_seed(csv_path, patients, synthetic, serum, history, SeedStage.PATIENTS)

    report = await run_seed(
        csv_path, patients, synthetic, serum, history, SeedStage.SYNTHETIC_PATIENTS
    )

    assert report.patients is None
    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=ROWS, without_patient=0
    )


async def test_only_synthetic_without_patients_inserts_nothing(
    csv_path: Path,
    patients: FakePatientRepository,
    synthetic: FakeSyntheticPatientRepository,
    serum: FakeSerumTestRepository,
    history: FakePatientHistoryRepository,
) -> None:
    report = await run_seed(
        csv_path, patients, synthetic, serum, history, SeedStage.SYNTHETIC_PATIENTS
    )

    assert report.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=0, without_patient=ROWS
    )
    assert patients.stored == {} and synthetic.stored == {}


async def test_replaying_the_full_seed_changes_nothing(
    csv_path: Path,
    serum_csv: Path,
    patients: FakePatientRepository,
    synthetic: FakeSyntheticPatientRepository,
    serum: FakeSerumTestRepository,
    history: FakePatientHistoryRepository,
) -> None:
    await run_seed(csv_path, patients, synthetic, serum, history, serum_csv_path=serum_csv)

    second = await run_seed(
        csv_path, patients, synthetic, serum, history, serum_csv_path=serum_csv
    )

    assert second.patients == PatientSeedReport(read=ROWS, inserted=0)
    assert second.synthetic_patients == SyntheticSeedReport(
        read=ROWS, inserted=0, without_patient=0
    )
    assert second.serum_tests == SerumSeedReport(read=2, inserted=0, without_patient=1)
    assert second.patient_history == HistorySeedReport(
        read=HISTORY_ROWS, inserted=0, without_patient=HISTORY_ROWS
    )
    assert patient_uuid_for("P-0") in patients.stored
    assert len(synthetic.stored) == ROWS


def test_the_report_tells_what_was_inserted_what_was_there_and_what_was_skipped() -> None:
    report = SeedReport(
        PatientSeedReport(read=10, inserted=4),
        SyntheticSeedReport(read=10, inserted=3, without_patient=2),
    )

    patients_line, synthetic_line = describe(report)

    assert "10 lignes lues, 4 insérés, 6 déjà présents" in patients_line
    assert "10 lignes lues, 3 insérés, 5 déjà présents, 2 sans patient" in synthetic_line


def test_the_serum_report_counts_rows_without_a_patient() -> None:
    line = describe(
        SeedReport(None, None, SerumSeedReport(read=4, inserted=3, without_patient=1))
    )[0]

    assert "4 lignes lues, 3 insérés, 0 déjà présents, 1 sans patient" in line


def test_the_history_report_counts_events_without_a_patient() -> None:
    line = describe(
        SeedReport(None, None, None, HistorySeedReport(read=7, inserted=7, without_patient=0))
    )[0]

    assert "7 événements, 7 insérés, 0 déjà présents, 0 sans patient" in line


def test_a_stage_that_did_not_run_is_not_reported() -> None:
    assert len(describe(SeedReport(PatientSeedReport(read=1, inserted=1), None))) == 1
    assert describe(SeedReport(None, None)) == []


# --- schéma obsolète et --reset ------------------------------------------------------------
# Pas d'outil de migration : `create_all` ne modifie pas une table qui existe déjà.


async def outdated_tables(*statements: str, create_current: bool = False) -> list[str]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        if create_current:
            await connection.run_sync(Base.metadata.create_all, tables=TABLES)
        for statement in statements:
            await connection.execute(text(statement))
        outdated = await connection.run_sync(find_outdated_tables)
    await engine.dispose()
    return outdated


async def test_no_table_is_not_an_outdated_schema() -> None:
    assert await outdated_tables() == []


async def test_tables_matching_the_entities_are_up_to_date() -> None:
    assert await outdated_tables(create_current=True) == []


async def test_a_table_created_before_a_column_was_added_is_detected() -> None:
    # `patients` d'avant `patient_id` : `create_all` ne la modifierait pas.
    old_patients = "create table patients (id char(32) primary key, firstname varchar(100))"

    assert await outdated_tables(old_patients) == ["patients"]


async def test_only_the_outdated_tables_are_reported() -> None:
    outdated = await outdated_tables(
        "drop table patients_synthetiques",
        "create table patients_synthetiques (id char(32) primary key, code_synthetique varchar(50))",
        create_current=True,
    )

    assert outdated == ["patients_synthetiques"]


def test_reset_recreates_both_tables_so_it_cannot_be_combined_with_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["seed", "--reset", "--only", "synthetic"])

    with pytest.raises(SystemExit):
        parse_args()


def test_reset_alone_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["seed", "--reset"])

    assert parse_args().reset is True
