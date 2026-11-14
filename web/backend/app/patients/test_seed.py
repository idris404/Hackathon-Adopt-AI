import uuid
from datetime import date
from pathlib import Path

import pytest

from app.conftest import FakePatientRepository, fake_seed_rows, fake_synthetic_row, write_seed_csv
from app.constants.patients import (
    SEED_CITIES,
    SEED_FEMALE_FIRSTNAMES,
    SEED_LASTNAMES,
    SEED_MALE_FIRSTNAMES,
    SEED_UUID_NAMESPACE,
    Gender,
)
from app.core.exceptions import SeedError
from app.patients import seed
from app.patients.seed import (
    build_patient_values,
    patient_uuid_for,
    read_patient_values,
    seed_patients,
)

pytestmark = pytest.mark.anyio


# --- une ligne du CSV --------------------------------------------------------------------


def test_the_patient_id_is_derived_from_the_csv_patient_id() -> None:
    assert patient_uuid_for("P-1") == uuid.uuid5(SEED_UUID_NAMESPACE, "P-1")
    assert patient_uuid_for("P-1") != patient_uuid_for("P-2")


def test_a_row_gives_the_patient_of_its_patient_id() -> None:
    values = build_patient_values(fake_synthetic_row(patient_id="P-1"), line=2)

    assert values["patient_id"] == "P-1"  # le `patient_id` du CSV est stocké tel quel
    assert values["id"] == patient_uuid_for("P-1")  # et la clé primaire en est déduite


def test_the_same_row_always_gives_the_same_identity() -> None:
    row = fake_synthetic_row()

    assert build_patient_values(row, line=2) == build_patient_values(row, line=2)


def test_birth_and_gender_come_from_the_csv() -> None:
    row = fake_synthetic_row(date_naissance="1991-01-25", sexe="F")

    values = build_patient_values(row, line=2)

    assert values["birth"] == date(1991, 1, 25)
    assert values["gender"] is Gender.FEMALE


def test_a_missing_birth_is_kept_as_null() -> None:
    assert build_patient_values(fake_synthetic_row(date_naissance=""), line=2)["birth"] is None


@pytest.mark.parametrize(
    ("gender", "firstnames"),
    [("M", SEED_MALE_FIRSTNAMES), ("F", SEED_FEMALE_FIRSTNAMES)],
)
def test_the_fake_identity_is_drawn_from_the_seed_lists(
    gender: str, firstnames: tuple[str, ...]
) -> None:
    for number in range(50):
        row = fake_synthetic_row(patient_id=f"P-{number}", sexe=gender)

        values = build_patient_values(row, line=2)

        assert values["firstname"] in firstnames
        assert values["lastname"] in SEED_LASTNAMES
        assert (values["city"], values["country"]) in SEED_CITIES


@pytest.mark.parametrize(
    "overrides",
    [{"patient_id": ""}, {"patient_id": "   "}, {"sexe": "X"}, {"sexe": ""},
     {"date_naissance": "25/01/1991"}],
)  # fmt: skip
def test_an_invalid_row_is_rejected_with_its_line_number(overrides: dict[str, str]) -> None:
    with pytest.raises(SeedError, match="ligne 7"):
        build_patient_values(fake_synthetic_row(**overrides), line=7)


def test_an_error_never_echoes_the_value_of_the_file() -> None:
    with pytest.raises(SeedError) as error:
        build_patient_values(fake_synthetic_row(date_naissance="valeur-secrete"), line=2)

    assert "valeur-secrete" not in str(error.value)


# --- lecture du fichier ------------------------------------------------------------------


def test_only_the_identity_columns_are_read(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(2), extra_column=True)

    values = list(read_patient_values(path))

    assert len(values) == 2
    assert set(values[0]) == {
        "id", "patient_id", "firstname", "lastname", "birth", "gender", "city", "country",
    }  # fmt: skip


def test_a_csv_without_the_identity_columns_is_rejected_and_names_them(tmp_path: Path) -> None:
    path = tmp_path / "patients.csv"
    path.write_text("patient_id,hla_A\nP-1,A2\n", encoding="utf-8")

    with pytest.raises(SeedError, match="date_naissance"):
        list(read_patient_values(path))


# --- ingestion ---------------------------------------------------------------------------


async def test_the_seed_ingests_in_batches_and_reports_the_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(seed, "SEED_BATCH_SIZE", 2)
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(5))
    repository = FakePatientRepository()

    report = await seed_patients(repository, path)

    assert repository.batches == [2, 2, 1]
    assert (report.read, report.inserted) == (5, 5)
    assert len(repository.stored) == 5


async def test_replaying_the_seed_does_not_duplicate_patients(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(3))
    repository = FakePatientRepository()

    await seed_patients(repository, path)
    second = await seed_patients(repository, path)

    assert len(repository.stored) == 3
    assert (second.read, second.inserted) == (3, 0)
