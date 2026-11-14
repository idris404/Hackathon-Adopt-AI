import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.conftest import AUTH_URL, FakePatientRepository, make_patient, make_serum_test
from app.constants.http import API_V1_PREFIX
from app.constants.patients import PATIENT_NOT_FOUND_CODE
from app.constants.signatures import (
    PATIENT_ALREADY_SIGNED_CODE,
    SIGN_QUEUE_PATH,
    SIGN_QUEUE_SIZE,
    SIGNATURES_ROUTER_PREFIX,
)
from app.main import app
from app.patients.entity import Patient
from app.patients.services import PatientService
from app.signatures.dependencies import get_signature_service
from app.signatures.entity import PatientSignature
from app.signatures.exceptions import PatientAlreadySignedError
from app.signatures.services import SignatureService

SIGNATURES_URL = f"{API_V1_PREFIX}{SIGNATURES_ROUTER_PREFIX}"
QUEUE_URL = f"{SIGNATURES_URL}{SIGN_QUEUE_PATH}"


class FakeSignatureRepository:
    """Remplace SignatureRepository. La requête de la file est testée à part
    (`signatures/test_repository.py`) : ici, tous les patients fournis sont éligibles."""

    def __init__(self, patients: list[Patient]) -> None:
        self.patients = patients
        self.signatures: dict[str, PatientSignature] = {}
        self.last_limit: int | None = None

    def _unsigned(self) -> list[Patient]:
        return [p for p in self.patients if p.patient_id not in self.signatures]

    async def eligible(self, limit: int) -> list[Patient]:
        self.last_limit = limit
        return self._unsigned()[:limit]

    async def count_eligible(self) -> int:
        return len(self._unsigned())

    async def add(self, patient_id: str, user_id: uuid.UUID) -> PatientSignature:
        if patient_id in self.signatures:
            raise PatientAlreadySignedError
        signature = PatientSignature(
            patient_id=patient_id, signed_by=user_id, signed_at=datetime.now(timezone.utc)
        )
        self.signatures[patient_id] = signature
        return signature


def constant_patient() -> Patient:
    patient = make_patient()
    patient.serum_tests = [make_serum_test(patient, profile="A")]
    return patient


@pytest.fixture
def repository() -> FakeSignatureRepository:
    return FakeSignatureRepository([constant_patient() for _ in range(SIGN_QUEUE_SIZE + 2)])


@pytest.fixture
def logged_in(
    client: TestClient, repository: FakeSignatureRepository, registered_user: dict[str, str]
) -> TestClient:
    patients = PatientService(FakePatientRepository(repository.patients))
    app.dependency_overrides[get_signature_service] = lambda: SignatureService(
        repository, patients
    )
    assert client.post(f"{AUTH_URL}/login", json=registered_user).status_code == 204
    return client


def test_the_queue_requires_authentication(client: TestClient) -> None:
    assert client.get(QUEUE_URL).status_code == 401


def test_signing_requires_authentication(client: TestClient) -> None:
    assert client.post(SIGNATURES_URL, json={"patient_id": str(uuid.uuid4())}).status_code == 401


def test_the_queue_returns_the_first_cases_and_the_remaining_count(
    logged_in: TestClient, repository: FakeSignatureRepository
) -> None:
    body = logged_in.get(QUEUE_URL).json()

    assert repository.last_limit == SIGN_QUEUE_SIZE
    assert len(body["items"]) == SIGN_QUEUE_SIZE
    assert body["remaining"] == SIGN_QUEUE_SIZE + 2
    assert body["items"][0]["serum_evolution"]["profile"] == "A"


def test_a_signed_patient_leaves_the_queue(
    logged_in: TestClient, repository: FakeSignatureRepository
) -> None:
    patient = repository.patients[0]
    me = logged_in.get(f"{API_V1_PREFIX}/users/me").json()

    response = logged_in.post(SIGNATURES_URL, json={"patient_id": str(patient.id)})

    assert response.status_code == 201
    body = response.json()
    assert (body["patient_id"], body["signed_by"]) == (patient.patient_id, me["id"])
    queue = logged_in.get(QUEUE_URL).json()
    assert str(patient.id) not in {item["id"] for item in queue["items"]}
    assert queue["remaining"] == SIGN_QUEUE_SIZE + 1


def test_signing_twice_is_a_409(logged_in: TestClient, repository: FakeSignatureRepository) -> None:
    payload = {"patient_id": str(repository.patients[0].id)}
    assert logged_in.post(SIGNATURES_URL, json=payload).status_code == 201

    response = logged_in.post(SIGNATURES_URL, json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": PATIENT_ALREADY_SIGNED_CODE}


def test_signing_an_unknown_patient_is_a_404(logged_in: TestClient) -> None:
    response = logged_in.post(SIGNATURES_URL, json={"patient_id": str(uuid.uuid4())})

    assert response.status_code == 404
    assert response.json() == {"detail": PATIENT_NOT_FOUND_CODE}


@pytest.mark.parametrize(
    "payload",
    [{}, {"patient_id": "not-a-uuid"}, {"patient_id": str(uuid.uuid4()), "signed_by": "me"}],
)
def test_an_invalid_body_is_a_422(logged_in: TestClient, payload: dict[str, str]) -> None:
    assert logged_in.post(SIGNATURES_URL, json=payload).status_code == 422
