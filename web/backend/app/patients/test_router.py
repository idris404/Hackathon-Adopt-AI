import uuid
from collections.abc import Callable
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.conftest import AUTH_URL, PATIENTS_URL, FakePatientRepository, make_patient
from app.constants.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SEARCH_MAX_LENGTH, SortOrder
from app.constants.patients import (
    DEFAULT_PATIENT_SORT_FIELD,
    PATIENT_NOT_FOUND_CODE,
    Gender,
    PatientSortField,
)
from app.main import app
from app.patients.dependencies import get_patient_service
from app.patients.entity import Patient
from app.patients.services import PatientService

PATIENT_FIELDS = {
    "id", "patient_id", "firstname", "lastname", "birth", "gender", "city", "country", "created_at",
}  # fmt: skip
PAGE_FIELDS = {"items", "total", "page", "page_size"}


def a_patient() -> Patient:
    return make_patient()


@pytest.fixture
def repository() -> FakePatientRepository:
    return FakePatientRepository([a_patient()])


@pytest.fixture
def logged_in(
    client: TestClient, repository: FakePatientRepository, registered_user: dict[str, str]
) -> TestClient:
    """Client connecté (vraie session, faux stockage) dont le service lit le faux repository."""
    app.dependency_overrides[get_patient_service] = lambda: PatientService(repository)
    assert client.post(f"{AUTH_URL}/login", json=registered_user).status_code == 204
    return client


# --- authentification --------------------------------------------------------------------


def test_the_list_requires_authentication(client: TestClient) -> None:
    assert client.get(PATIENTS_URL).status_code == 401


def test_a_patient_requires_authentication(client: TestClient) -> None:
    assert client.get(f"{PATIENTS_URL}/{uuid.uuid4()}").status_code == 401


# --- liste -------------------------------------------------------------------------------


def test_the_list_returns_a_paginated_page_of_patients(logged_in: TestClient) -> None:
    response = logged_in.get(PATIENTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAGE_FIELDS
    assert body["total"] == 1
    assert set(body["items"][0]) == PATIENT_FIELDS


def test_the_list_applies_the_documented_defaults(
    logged_in: TestClient, repository: FakePatientRepository
) -> None:
    body = logged_in.get(PATIENTS_URL).json()

    assert (body["page"], body["page_size"]) == (1, DEFAULT_PAGE_SIZE)
    assert repository.last_criteria is not None
    assert repository.last_criteria.sort_by == DEFAULT_PATIENT_SORT_FIELD
    assert repository.last_criteria.sort_order is SortOrder.ASC


def test_the_list_forwards_search_filters_sort_and_page(
    logged_in: TestClient, repository: FakePatientRepository
) -> None:
    response = logged_in.get(
        PATIENTS_URL,
        params={
            "search": "dup",
            "gender": Gender.FEMALE,
            "city": "Lyon",
            "country": "France",
            "birth_from": "1980-01-01",
            "birth_to": "1990-12-31",
            "sort_by": PatientSortField.BIRTH,
            "sort_order": SortOrder.DESC,
            "page": 2,
            "page_size": 5,
        },
    )

    assert response.status_code == 200
    criteria = repository.last_criteria
    assert criteria is not None
    assert criteria.search == "dup"
    assert criteria.gender is Gender.FEMALE
    assert (criteria.city, criteria.country) == ("Lyon", "France")
    assert (criteria.birth_from, criteria.birth_to) == (date(1980, 1, 1), date(1990, 12, 31))
    assert (criteria.sort_by, criteria.sort_order) == (PatientSortField.BIRTH, SortOrder.DESC)
    assert (criteria.offset, criteria.limit) == (5, 5)


def test_an_empty_search_is_accepted_as_no_search(logged_in: TestClient) -> None:
    # Un champ de recherche vide, envoyé tel quel par un formulaire, ne doit pas être une erreur.
    assert logged_in.get(PATIENTS_URL, params={"search": ""}).status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": MAX_PAGE_SIZE + 1},
        {"sort_by": "hashed_password"},  # hors liste blanche
        {"sort_by": "lastname; DROP TABLE patients"},
        {"sort_order": "sideways"},
        {"gender": "X"},
        {"search": "x" * (SEARCH_MAX_LENGTH + 1)},
        {"birth_from": "not-a-date"},
        {"birth_from": "2000-01-01", "birth_to": "1990-01-01"},  # bornes inversées
        {"serach": "typo"},  # paramètre inconnu : refusé, pas ignoré
    ],
)
def test_an_invalid_query_is_rejected(logged_in: TestClient, params: dict[str, object]) -> None:
    assert logged_in.get(PATIENTS_URL, params=params).status_code == 422


def test_the_largest_allowed_page_size_is_accepted(logged_in: TestClient) -> None:
    assert logged_in.get(PATIENTS_URL, params={"page_size": MAX_PAGE_SIZE}).status_code == 200


# --- un patient --------------------------------------------------------------------------


def test_a_patient_is_returned_by_id(
    logged_in: TestClient, repository: FakePatientRepository
) -> None:
    patient = repository.patients[0]

    response = logged_in.get(f"{PATIENTS_URL}/{patient.id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PATIENT_FIELDS
    assert body["id"] == str(patient.id)


def test_an_unknown_patient_is_a_404(logged_in: TestClient) -> None:
    response = logged_in.get(f"{PATIENTS_URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": PATIENT_NOT_FOUND_CODE}


def test_a_malformed_id_is_a_422(logged_in: TestClient) -> None:
    assert logged_in.get(f"{PATIENTS_URL}/not-a-uuid").status_code == 422


def test_patients_are_read_only(
    logged_in: TestClient, repository: FakePatientRepository
) -> None:
    patient_url = f"{PATIENTS_URL}/{repository.patients[0].id}"
    for method in (logged_in.post, logged_in.put, logged_in.patch, logged_in.delete):
        assert method(PATIENTS_URL).status_code == 405
        assert method(patient_url).status_code == 405
