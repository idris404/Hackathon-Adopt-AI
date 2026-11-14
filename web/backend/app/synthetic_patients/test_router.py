import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.conftest import (
    AUTH_URL,
    SYNTHETIC_PATIENTS_URL,
    FakePatientRepository,
    FakeSyntheticPatientRepository,
    fake_synthetic_row,
    make_patient,
    patient_synthetic_patients_url,
)
from app.constants.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SEARCH_MAX_LENGTH, SortOrder
from app.constants.patients import PATIENT_CODE_MAX_LENGTH, PATIENT_NOT_FOUND_CODE, Gender
from app.constants.synthetic_patients import (
    DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD,
    SyntheticPatientSortField,
)
from app.main import app
from app.patients.entity import Patient
from app.patients.services import PatientService
from app.synthetic_patients.dependencies import get_synthetic_patient_service
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.seed import build_synthetic_values
from app.synthetic_patients.services import SyntheticPatientService

PAGE_FIELDS = {"items", "total", "page", "page_size"}


def a_synthetic_patient() -> SyntheticPatient:
    values = build_synthetic_values(fake_synthetic_row(), line=2)
    return SyntheticPatient(**values, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


@pytest.fixture
def repository() -> FakeSyntheticPatientRepository:
    return FakeSyntheticPatientRepository([a_synthetic_patient()])


@pytest.fixture
def patient() -> Patient:
    return make_patient()


@pytest.fixture
def logged_in(
    client: TestClient,
    repository: FakeSyntheticPatientRepository,
    patient: Patient,
    registered_user: dict[str, str],
) -> TestClient:
    """Client connecté (vraie session, faux stockage) ; `patient` est le seul patient qui existe."""
    patients = PatientService(FakePatientRepository([patient]))
    app.dependency_overrides[get_synthetic_patient_service] = lambda: SyntheticPatientService(
        repository, patients
    )
    assert client.post(f"{AUTH_URL}/login", json=registered_user).status_code == 204
    return client


def test_the_list_requires_authentication(client: TestClient) -> None:
    assert client.get(SYNTHETIC_PATIENTS_URL).status_code == 401


def test_the_list_returns_a_paginated_page(logged_in: TestClient) -> None:
    response = logged_in.get(SYNTHETIC_PATIENTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAGE_FIELDS
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_an_item_has_every_column_of_the_table_under_its_csv_name(logged_in: TestClient) -> None:
    item = logged_in.get(SYNTHETIC_PATIENTS_URL).json()["items"][0]

    assert set(item) == {column.name for column in SyntheticPatient.__table__.columns}
    assert item["_verite_tgi"] == 0.25  # les colonnes `_…` gardent leur nom
    assert item["sexe"] == "M"
    assert item["synthetic"] is True
    assert item["date_reference"] == "2020-01-31"


def test_the_list_applies_the_documented_defaults(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository
) -> None:
    body = logged_in.get(SYNTHETIC_PATIENTS_URL).json()

    assert (body["page"], body["page_size"]) == (1, DEFAULT_PAGE_SIZE)
    assert repository.last_criteria is not None
    assert repository.last_criteria.sort_by == DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD
    assert repository.last_criteria.sort_order is SortOrder.ASC


def test_the_list_forwards_search_filters_sort_and_page(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository
) -> None:
    patient_id = "SYN-0001"

    response = logged_in.get(
        SYNTHETIC_PATIENTS_URL,
        params={
            "search": "SYN",
            "patient_id": patient_id,
            "sexe": Gender.FEMALE,
            "jeu": "actuel",
            "phase": "pre_greffe",
            "statut_parcours": "En attente de greffe",
            "organe": "Rein",
            "sort_by": SyntheticPatientSortField.AGE,
            "sort_order": SortOrder.DESC,
            "page": 2,
            "page_size": 5,
        },
    )

    assert response.status_code == 200
    criteria = repository.last_criteria
    assert criteria is not None
    assert (criteria.search, criteria.patient_id, criteria.sexe) == ("SYN", patient_id, Gender.FEMALE)
    assert (criteria.jeu, criteria.phase, criteria.organe) == ("actuel", "pre_greffe", "Rein")
    assert criteria.statut_parcours == "En attente de greffe"
    assert (criteria.sort_by, criteria.sort_order) == (SyntheticPatientSortField.AGE, SortOrder.DESC)
    assert (criteria.offset, criteria.limit) == (5, 5)


def test_empty_filters_are_accepted_as_no_filter(logged_in: TestClient) -> None:
    # Un formulaire envoie ses champs vides tels quels : ce n'est pas une erreur.
    params = {"search": "", "jeu": "", "phase": "", "organe": ""}

    assert logged_in.get(SYNTHETIC_PATIENTS_URL, params=params).status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": MAX_PAGE_SIZE + 1},
        {"sort_by": "_verite_tgi"},  # une vérité terrain n'est pas triable
        {"sort_by": "hla_a"},  # hors liste blanche
        {"sort_by": "age; DROP TABLE patients_synthetiques"},
        {"sort_order": "sideways"},
        {"sexe": "X"},
        {"patient_id": "x" * (PATIENT_CODE_MAX_LENGTH + 1)},
        {"search": "x" * (SEARCH_MAX_LENGTH + 1)},
        {"serach": "typo"},  # paramètre inconnu : refusé, pas ignoré
    ],
)
def test_an_invalid_query_is_rejected(logged_in: TestClient, params: dict[str, object]) -> None:
    assert logged_in.get(SYNTHETIC_PATIENTS_URL, params=params).status_code == 422


def test_the_largest_allowed_page_size_is_accepted(logged_in: TestClient) -> None:
    response = logged_in.get(SYNTHETIC_PATIENTS_URL, params={"page_size": MAX_PAGE_SIZE})

    assert response.status_code == 200


def test_synthetic_patients_are_read_only(logged_in: TestClient) -> None:
    for method in (logged_in.post, logged_in.put, logged_in.patch, logged_in.delete):
        assert method(SYNTHETIC_PATIENTS_URL).status_code == 405


# --- GET /patients/{patient_id}/synthetic-patients ---------------------------------------


def test_the_synthetic_patients_of_a_patient_require_authentication(
    client: TestClient, patient: Patient
) -> None:
    assert client.get(patient_synthetic_patients_url(patient.id)).status_code == 401


def test_the_synthetic_patients_of_a_patient_are_returned_as_a_page(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository, patient: Patient
) -> None:
    response = logged_in.get(patient_synthetic_patients_url(patient.id))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAGE_FIELDS
    assert body["total"] == 1
    assert set(body["items"][0]) == {c.name for c in SyntheticPatient.__table__.columns}
    # L'URL désigne le patient par son `id` (UUID) ; c'est son `patient_id` qui sert de liaison.
    assert repository.last_criteria is not None
    assert repository.last_criteria.patient_id == patient.patient_id


def test_the_nested_list_forwards_sort_and_page(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository, patient: Patient
) -> None:
    response = logged_in.get(
        patient_synthetic_patients_url(patient.id),
        params={"sort_by": SyntheticPatientSortField.AGE, "sort_order": SortOrder.DESC,
                "page": 2, "page_size": 5},
    )  # fmt: skip

    assert response.status_code == 200
    criteria = repository.last_criteria
    assert criteria is not None
    assert (criteria.sort_by, criteria.sort_order) == (SyntheticPatientSortField.AGE, SortOrder.DESC)
    assert (criteria.offset, criteria.limit) == (5, 5)


def test_a_patient_without_synthetic_patients_gets_an_empty_page(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository, patient: Patient
) -> None:
    repository.synthetic_patients = []

    body = logged_in.get(patient_synthetic_patients_url(patient.id)).json()

    assert (body["items"], body["total"]) == ([], 0)


def test_an_unknown_patient_is_a_404_not_an_empty_page(
    logged_in: TestClient, repository: FakeSyntheticPatientRepository
) -> None:
    response = logged_in.get(patient_synthetic_patients_url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json() == {"detail": PATIENT_NOT_FOUND_CODE}
    assert repository.last_criteria is None


def test_a_malformed_patient_id_is_a_422(logged_in: TestClient) -> None:
    assert logged_in.get(patient_synthetic_patients_url("not-a-uuid")).status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": MAX_PAGE_SIZE + 1},
        {"sort_by": "_verite_tgi"},
        {"sort_order": "sideways"},
        # Le patient est dans l'URL : les filtres de la liste globale n'ont pas leur place ici.
        {"patient_id": str(uuid.uuid4())},
        {"jeu": "actuel"},
        {"search": "SYN"},
    ],
)
def test_an_invalid_nested_query_is_rejected(
    logged_in: TestClient, patient: Patient, params: dict[str, object]
) -> None:
    response = logged_in.get(patient_synthetic_patients_url(patient.id), params=params)

    assert response.status_code == 422


def test_the_nested_route_is_read_only(logged_in: TestClient, patient: Patient) -> None:
    url = patient_synthetic_patients_url(patient.id)
    for method in (logged_in.post, logged_in.put, logged_in.patch, logged_in.delete):
        assert method(url).status_code == 405
