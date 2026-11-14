import uuid
from datetime import date
from pathlib import Path

import pytest

from app.conftest import (
    UNKNOWN_CSV_COLUMN,
    FakePatientRepository,
    FakeSyntheticPatientRepository,
    fake_seed_rows,
    fake_synthetic_row,
    make_patient,
    write_seed_csv,
)
from app.constants.patients import Gender
from app.constants.seed import ASYNCPG_MAX_QUERY_ARGUMENTS, SEED_BATCH_SIZE
from app.constants.synthetic_patients import (
    SEED_SYNTHETIC_UUID_NAMESPACE,
    SYNTHETIC_NON_CSV_COLUMNS,
)
from app.core.exceptions import SeedError
from app.patients.services import PatientService
from app.synthetic_patients import seed
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.seed import (
    SYNTHETIC_CSV_COLUMNS,
    build_synthetic_values,
    column_name_for,
    read_synthetic_values,
    seed_synthetic_patients,
)

pytestmark = pytest.mark.anyio


# --- une ligne du CSV --------------------------------------------------------------------


def test_a_synthetic_patient_has_every_column_of_the_csv_plus_its_id() -> None:
    values = build_synthetic_values(fake_synthetic_row(), line=2)

    table_columns = {column.name for column in SyntheticPatient.__table__.columns}
    assert set(values) == table_columns - {"created_at"}  # `created_at` : défaut du serveur


def test_the_csv_patient_id_is_the_link_to_the_patient() -> None:
    values = build_synthetic_values(fake_synthetic_row(patient_id="P-1"), line=2)

    # Le `patient_id` du CSV est repris tel quel : c'est la clé étrangère vers `patients.patient_id`.
    assert values["patient_id"] == "P-1"
    assert values["id"] == uuid.uuid5(SEED_SYNTHETIC_UUID_NAMESPACE, "P-1")


def test_values_are_converted_to_the_type_of_their_column() -> None:
    values = build_synthetic_values(fake_synthetic_row(), line=2)

    assert values["date_reference"] == date(2020, 1, 31)
    assert values["age"] == 3
    assert values["synthetic"] is True
    assert values["_verite_tgi"] == 0.25
    assert values["sexe"] is Gender.MALE
    assert values["phase"] == "texte"


def test_csv_headers_are_matched_to_columns_ignoring_case() -> None:
    assert column_name_for("hla_A") == "hla_a"
    assert column_name_for("_verite_p_rejet") == "_verite_p_rejet"
    assert column_name_for("patient_id") == "patient_id"


def test_an_empty_value_is_null_when_the_column_allows_it() -> None:
    values = build_synthetic_values(fake_synthetic_row(age="", _rejet_1an=""), line=2)

    assert values["age"] is None
    assert values["_rejet_1an"] is None


def test_an_empty_value_is_rejected_when_the_column_requires_one() -> None:
    with pytest.raises(SeedError, match="ligne 7 : colonne organe vide"):
        build_synthetic_values(fake_synthetic_row(organe=""), line=7)


def test_a_row_without_a_patient_id_is_rejected() -> None:
    # Sans `patient_id`, pas de lien vers un patient.
    with pytest.raises(SeedError, match="ligne 7 : colonne patient_id vide"):
        build_synthetic_values(fake_synthetic_row(patient_id=""), line=7)


@pytest.mark.parametrize(
    ("column", "bad_value"),
    [
        ("date_reference", "31/12/2026"),
        ("age", "trente"),
        ("_verite_tgi", "beaucoup"),
        ("synthetic", "oui"),  # un booléen s'écrit true / false
        ("sexe", "X"),
    ],
)
def test_an_unreadable_value_is_rejected_without_echoing_it(column: str, bad_value: str) -> None:
    with pytest.raises(SeedError) as error:
        build_synthetic_values(fake_synthetic_row(**{column: bad_value}), line=7)

    assert f"ligne 7 : colonne {column} invalide" in str(error.value)
    assert bad_value not in str(error.value)


# --- lecture du fichier ------------------------------------------------------------------


def test_every_csv_column_is_read_and_unknown_ones_are_ignored(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(2), extra_column=True)

    values = list(read_synthetic_values(path))

    assert len(values) == 2
    assert UNKNOWN_CSV_COLUMN not in values[0]
    links = SYNTHETIC_NON_CSV_COLUMNS - {"created_at"}  # `created_at` : défaut du serveur
    assert set(values[0]) == set(SYNTHETIC_CSV_COLUMNS) | links


def test_a_csv_missing_a_column_is_rejected_and_names_it(tmp_path: Path) -> None:
    incomplete = [{k: v for k, v in row.items() if k != "organe"} for row in fake_seed_rows(1)]
    path = write_seed_csv(tmp_path / "patients.csv", incomplete)

    with pytest.raises(SeedError, match="organe"):
        list(read_synthetic_values(path))


def test_an_invalid_line_stops_the_read_and_says_which(tmp_path: Path) -> None:
    data = fake_seed_rows(3)
    data[2]["date_reference"] = "pas-une-date"  # 3e donnée = ligne 4 du fichier
    path = write_seed_csv(tmp_path / "patients.csv", data)

    with pytest.raises(SeedError, match="ligne 4"):
        list(read_synthetic_values(path))


def test_a_batch_never_exceeds_the_asyncpg_parameter_limit() -> None:
    columns = len(SyntheticPatient.__table__.columns)

    assert SEED_BATCH_SIZE * columns <= ASYNCPG_MAX_QUERY_ARGUMENTS


# --- ingestion à partir des patients -----------------------------------------------------


def patients_service_knowing(count: int) -> PatientService:
    """Un service patients dont les seuls patients ont les `patient_id` P-0 … P-(count-1)."""
    patients = [make_patient(patient_id=f"P-{n}") for n in range(count)]
    return PatientService(FakePatientRepository(patients))


async def test_every_row_whose_patient_exists_is_inserted_with_its_patient_id(
    tmp_path: Path,
) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(3))
    repository = FakeSyntheticPatientRepository()

    report = await seed_synthetic_patients(repository, patients_service_knowing(3), path)

    assert (report.read, report.inserted, report.without_patient) == (3, 3, 0)
    assert {v["patient_id"] for v in repository.stored.values()} == {"P-0", "P-1", "P-2"}


async def test_a_row_without_a_patient_is_counted_and_not_inserted(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(5))
    repository = FakeSyntheticPatientRepository()

    report = await seed_synthetic_patients(repository, patients_service_knowing(2), path)

    assert (report.read, report.inserted, report.without_patient) == (5, 2, 3)
    assert {v["patient_id"] for v in repository.stored.values()} == {"P-0", "P-1"}


async def test_without_any_patient_nothing_is_inserted(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(3))
    repository = FakeSyntheticPatientRepository()

    report = await seed_synthetic_patients(repository, patients_service_knowing(0), path)

    assert (report.inserted, report.without_patient) == (0, 3)
    assert repository.batches == []  # même pas une requête d'insertion vide


async def test_the_seed_works_in_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(seed, "SEED_BATCH_SIZE", 2)
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(5))
    repository = FakeSyntheticPatientRepository()

    report = await seed_synthetic_patients(repository, patients_service_knowing(5), path)

    assert repository.batches == [2, 2, 1]
    assert report.inserted == 5


async def test_replaying_the_seed_does_not_duplicate_anything(tmp_path: Path) -> None:
    path = write_seed_csv(tmp_path / "patients.csv", fake_seed_rows(3))
    repository = FakeSyntheticPatientRepository()
    patients = patients_service_knowing(3)

    await seed_synthetic_patients(repository, patients, path)
    second = await seed_synthetic_patients(repository, patients, path)

    assert len(repository.stored) == 3
    assert (second.read, second.inserted, second.without_patient) == (3, 0, 0)
