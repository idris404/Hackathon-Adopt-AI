import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.conftest import (
    AUTH_URL,
    SYNTHETIC_PATIENTS_URL,
    FakeSyntheticPatientRepository,
    fake_synthetic_row,
)
from app.constants.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SEARCH_MAX_LENGTH, SortOrder
from app.constants.patients import Gender
from app.constants.synthetic_patients import (
    DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD,
    SyntheticPatientSortField,
)
from app.main import app
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
def logged_in(
    client: TestClient,
    repository: FakeSyntheticPatientRepository,
    registered_user: dict[str, str],
) -> TestClient:
    """Client connecté (vraie session, faux stockage) dont le service lit le faux repository."""
    app.dependency_overrides[get_synthetic_patient_service] = lambda: SyntheticPatientService(
        repository
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
    patient_id = uuid.uuid4()

    response = logged_in.get(
        SYNTHETIC_PATIENTS_URL,
        params={
            "search": "SYN",
            "patient_id": str(patient_id),
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
        {"patient_id": "not-a-uuid"},
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
