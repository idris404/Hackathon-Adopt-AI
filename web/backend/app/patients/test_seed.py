import uuid
from datetime import date
from pathlib import Path

import pytest

from app.conftest import FakePatientRepository
from app.constants.patients import (
    CSV_COLUMN_BIRTH,
    CSV_COLUMN_GENDER,
    CSV_COLUMN_PATIENT_ID,
    SEED_CITIES,
    SEED_FEMALE_FIRSTNAMES,
    SEED_LASTNAMES,
    SEED_MALE_FIRSTNAMES,
    SEED_UUID_NAMESPACE,
    Gender,
)
from app.patients import seed
from app.patients.exceptions import PatientSeedError
from app.patients.seed import build_patient_values, read_patient_values, seed_patients

pytestmark = pytest.mark.anyio

# Un en-tête avec une colonne clinique en plus : elle doit être ignorée.
HEADER = f"{CSV_COLUMN_PATIENT_ID},{CSV_COLUMN_BIRTH},{CSV_COLUMN_GENDER},hla_A"


def row(patient_id: str = "P-1", birth: str = "1991-01-25", gender: str = "M") -> dict[str, str]:
    return {
        CSV_COLUMN_PATIENT_ID: patient_id,
        CSV_COLUMN_BIRTH: birth,
        CSV_COLUMN_GENDER: gender,
    }


def write_csv(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return path


# --- une ligne du CSV --------------------------------------------------------------------


def test_the_id_is_derived_from_the_csv_patient_id() -> None:
    values = build_patient_values(row("P-1"), line=2)

    assert values["id"] == uuid.uuid5(SEED_UUID_NAMESPACE, "P-1")
    assert build_patient_values(row("P-2"), line=3)["id"] != values["id"]


def test_the_same_row_always_gives_the_same_identity() -> None:
    assert build_patient_values(row(), line=2) == build_patient_values(row(), line=2)


def test_birth_and_gender_come_from_the_csv() -> None:
    values = build_patient_values(row(birth="1991-01-25", gender="F"), line=2)

    assert values["birth"] == date(1991, 1, 25)
    assert values["gender"] is Gender.FEMALE


def test_a_missing_birth_is_kept_as_null() -> None:
    assert build_patient_values(row(birth=""), line=2)["birth"] is None


@pytest.mark.parametrize(
    ("gender", "firstnames"),
    [("M", SEED_MALE_FIRSTNAMES), ("F", SEED_FEMALE_FIRSTNAMES)],
)
def test_the_fake_identity_is_drawn_from_the_seed_lists(
    gender: str, firstnames: tuple[str, ...]
) -> None:
    for number in range(50):
        values = build_patient_values(row(f"P-{number}", gender=gender), line=2)

        assert values["firstname"] in firstnames
        assert values["lastname"] in SEED_LASTNAMES
        assert (values["city"], values["country"]) in SEED_CITIES


# --- erreurs -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_row", [row(patient_id=""), row(patient_id="   "), row(gender="X"), row(gender=""),
                row(birth="25/01/1991")],
)  # fmt: skip
def test_an_invalid_row_is_rejected_with_its_line_number(bad_row: dict[str, str]) -> None:
    with pytest.raises(PatientSeedError, match="ligne 7"):
        build_patient_values(bad_row, line=7)


def test_an_error_never_echoes_the_value_of_the_file() -> None:
    with pytest.raises(PatientSeedError) as error:
        build_patient_values(row(birth="valeur-secrete"), line=2)

    assert "valeur-secrete" not in str(error.value)


def test_a_csv_without_the_identity_columns_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "patients.csv"
    path.write_text("patient_id,hla_A\nP-1,A2\n", encoding="utf-8")

    with pytest.raises(PatientSeedError, match=CSV_COLUMN_BIRTH):
        list(read_patient_values(path))


# --- lecture et ingestion ----------------------------------------------------------------


def test_the_csv_is_read_and_clinical_columns_are_ignored(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "patients.csv", ["P-1,1991-01-25,M,A2 A2", "P-2,,F,A1 A3"])

    rows = list(read_patient_values(path))

    assert [r["birth"] for r in rows] == [date(1991, 1, 25), None]
    assert not any("hla_A" in r for r in rows)


async def test_the_seed_ingests_in_batches_and_reports_the_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(seed, "SEED_BATCH_SIZE", 2)
    path = write_csv(tmp_path / "patients.csv", [f"P-{n},1990-01-01,M,A2" for n in range(5)])
    repository = FakePatientRepository()

    report = await seed_patients(repository, path)

    assert repository.batches == [2, 2, 1]
    assert (report.read, report.inserted, report.already_present) == (5, 5, 0)


async def test_replaying_the_seed_does_not_duplicate_patients(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "patients.csv", [f"P-{n},1990-01-01,F,A2" for n in range(3)])
    repository = FakePatientRepository()

    await seed_patients(repository, path)
    second = await seed_patients(repository, path)

    assert len(repository.stored) == 3
    assert (second.read, second.inserted, second.already_present) == (3, 0, 3)
