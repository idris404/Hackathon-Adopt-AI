"""Fixtures partagées par tous les contextes.

Aucun test ne touche PostgreSQL : l'accès aux données est remplacé par des faux en
mémoire via `app.dependency_overrides`. Les tests n'utilisent pas `TestClient` comme
gestionnaire de contexte, donc le `lifespan` (création des tables) ne s'exécute pas.
"""

import os

# La config est lue à l'import de `app` : ces valeurs doivent être posées avant.
# Elles écrasent `web/.env` pour que la suite soit identique sur toutes les machines.
os.environ.update(
    {
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_NAME": "test_db",
        "DB_PORT": "5432",
        "FRONTEND_URL": "http://frontend.test",
        "COOKIE_SECURE": "true",
    }
)

import csv  # noqa: E402
import uuid  # noqa: E402
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from fastapi_users.db import BaseUserDatabase  # noqa: E402

from app.auth.dependencies import get_access_token_db  # noqa: E402
from app.constants.analysis import ANALYSIS_ROUTER_PREFIX  # noqa: E402
from app.constants.auth import AUTH_ROUTER_PREFIX, PASSWORD_MIN_LENGTH  # noqa: E402
from app.constants.http import API_V1_PREFIX  # noqa: E402
from app.constants.patient_history import HistoryKind  # noqa: E402
from app.constants.patients import PATIENTS_ROUTER_PREFIX, Gender  # noqa: E402
from app.constants.seed import CSV_COLUMN_PATIENT_ID  # noqa: E402
from app.constants.synthetic_patients import SYNTHETIC_PATIENTS_ROUTER_PREFIX  # noqa: E402
from app.constants.users import USERS_ROUTER_PREFIX  # noqa: E402
from app.main import app  # noqa: E402
from app.patient_history.entity import PatientHistory  # noqa: E402
from app.patients.entity import Patient  # noqa: E402
from app.patients.repository import PatientCriteria  # noqa: E402
from app.serum_tests.entity import SerumTest
from app.synthetic_patients.entity import SyntheticPatient  # noqa: E402
from app.synthetic_patients.repository import SyntheticPatientCriteria  # noqa: E402
from app.synthetic_patients.seed import SYNTHETIC_CSV_COLUMNS  # noqa: E402
from app.users.dependencies import get_user_db  # noqa: E402

# https : le cookie de session est `Secure`, le client de test ne le renvoie qu'en https.
TEST_BASE_URL = "https://testserver"

# URLs de l'API v1, construites comme main.py : version + préfixe du contexte.
AUTH_URL = f"{API_V1_PREFIX}{AUTH_ROUTER_PREFIX}"
USERS_URL = f"{API_V1_PREFIX}{USERS_ROUTER_PREFIX}"
ANALYSIS_URL = f"{API_V1_PREFIX}{ANALYSIS_ROUTER_PREFIX}"
PATIENTS_URL = f"{API_V1_PREFIX}{PATIENTS_ROUTER_PREFIX}"
SYNTHETIC_PATIENTS_URL = f"{API_V1_PREFIX}{SYNTHETIC_PATIENTS_ROUTER_PREFIX}"


def patient_synthetic_patients_url(patient_id: uuid.UUID | str) -> str:
    """`/api/v1/patients/{patient_id}/synthetic-patients`, construite comme main.py."""
    return f"{PATIENTS_URL}/{patient_id}{SYNTHETIC_PATIENTS_ROUTER_PREFIX}"


@dataclass
class FakeUser:
    email: str
    hashed_password: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False


class FakeUserDatabase(BaseUserDatabase[FakeUser, uuid.UUID]):
    """Remplace SQLAlchemyUserDatabase. Comme lui, compare les emails sans tenir compte de la casse."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, FakeUser] = {}

    async def get(self, id: uuid.UUID) -> FakeUser | None:
        return self.users.get(id)

    async def get_by_email(self, email: str) -> FakeUser | None:
        return next(
            (user for user in self.users.values() if user.email.lower() == email.lower()),
            None,
        )

    async def create(self, create_dict: dict[str, Any]) -> FakeUser:
        user = FakeUser(**create_dict)
        self.users[user.id] = user
        return user

    async def update(self, user: FakeUser, update_dict: dict[str, Any]) -> FakeUser:
        for key, value in update_dict.items():
            setattr(user, key, value)
        return user

    async def delete(self, user: FakeUser) -> None:
        del self.users[user.id]


@dataclass
class FakeAccessToken:
    token: str
    user_id: uuid.UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FakeAccessTokenDatabase:
    """Remplace SQLAlchemyAccessTokenDatabase. Applique `max_age` comme la requête SQL."""

    def __init__(self) -> None:
        self.tokens: dict[str, FakeAccessToken] = {}

    async def get_by_token(
        self, token: str, max_age: datetime | None = None
    ) -> FakeAccessToken | None:
        access_token = self.tokens.get(token)
        if access_token is None:
            return None
        if max_age is not None and access_token.created_at < max_age:
            return None
        return access_token

    async def create(self, create_dict: dict[str, Any]) -> FakeAccessToken:
        access_token = FakeAccessToken(**create_dict)
        self.tokens[access_token.token] = access_token
        return access_token

    async def update(
        self, access_token: FakeAccessToken, update_dict: dict[str, Any]
    ) -> FakeAccessToken:
        for key, value in update_dict.items():
            setattr(access_token, key, value)
        return access_token

    async def delete(self, access_token: FakeAccessToken) -> None:
        del self.tokens[access_token.token]

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        self.tokens = {
            token: access_token
            for token, access_token in self.tokens.items()
            if access_token.user_id != user_id
        }


def fake_synthetic_row(**overrides: str) -> dict[str, str]:
    """Une ligne de CSV complète, aux valeurs fictives. Clés = en-têtes du CSV (`patient_id`…).

    Générée depuis les types de l'entité : aucune ligne du vrai CSV n'est recopiée dans les tests.
    """
    by_type = {bool: "true", date: "2020-01-31", int: "3", float: "0.25", Gender: "M"}
    row = {
        name: by_type.get(column.type.python_type, "texte")
        for name, column in SYNTHETIC_CSV_COLUMNS.items()
    }
    row[CSV_COLUMN_PATIENT_ID] = "P-1"
    return row | overrides


def make_patient(**overrides: object) -> Patient:
    """Un patient fictif (en mémoire). `patient_id` est unique d'un appel à l'autre."""
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "patient_id": f"P-{uuid.uuid4().hex[:12]}",
        "firstname": "Ada",
        "lastname": "Test",
        "birth": date(1985, 3, 2),
        "gender": Gender.FEMALE,
        "city": "Lille",
        "country": "France",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    patient = Patient(**(values | overrides))
    patient.serum_tests = []
    patient.history = []
    return patient


def make_serum_test(patient: Patient, **overrides: object) -> SerumTest:
    """Un test sérique fictif, lié au patient par son `patient_id`."""
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "patient_id": patient.patient_id,
        "graft_date": date(2016, 8, 4),
        "test_date": date(2017, 12, 9),
        "b12": 40,
        "b12_output": 0,
        "b13": 190,
        "b13_output": 0,
        "dr53": 291,
        "dr53_output": 0,
        "dr51": 177,
        "dr51_output": 0,
        "dq10": 1870,
        "dq10_output": 1,
        "profile": "C",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    return SerumTest(**(values | overrides))


UNKNOWN_CSV_COLUMN = "colonne_inconnue_de_la_table"


def fake_seed_rows(count: int, **overrides: str) -> list[dict[str, str]]:
    """`count` lignes de CSV fictives, de codes distincts (P-0, P-1, …)."""
    return [fake_synthetic_row(patient_id=f"P-{n}", **overrides) for n in range(count)]


def write_seed_csv(path: Path, rows: list[dict[str, str]], extra_column: bool = False) -> Path:
    """Écrit un CSV à ingérer. `extra_column` ajoute une colonne inconnue de la table."""
    fieldnames = list(rows[0]) + ([UNKNOWN_CSV_COLUMN] if extra_column else [])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, restval="ignored")
        writer.writeheader()
        writer.writerows(rows)
    return path


def insert_ignoring_existing(
    stored: dict[uuid.UUID, Mapping[str, object]], values: Sequence[Mapping[str, object]]
) -> int:
    """Comme `ON CONFLICT DO NOTHING` : ce qui existe déjà n'est pas réinséré."""
    new = {value["id"]: value for value in values if value["id"] not in stored}
    stored.update(new)
    return len(new)


class FakePatientRepository:
    """Remplace PatientRepository. Ne filtre ni ne trie : la requête SQL est testée à part
    (`patients/test_repository.py`). Garde le dernier critère reçu pour vérifier le mapping."""

    def __init__(self, patients: list[Patient] | None = None) -> None:
        self.patients: list[Patient] = patients or []
        self.total: int | None = None  # None : le nombre de patients fournis
        self.last_criteria: PatientCriteria | None = None
        self.stored: dict[uuid.UUID, Mapping[str, object]] = {}  # patients insérés par le seed
        self.batches: list[int] = []

    async def find(self, criteria: PatientCriteria) -> tuple[list[Patient], int]:
        self.last_criteria = criteria
        return self.patients, len(self.patients) if self.total is None else self.total

    async def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return next((patient for patient in self.patients if patient.id == patient_id), None)

    async def existing_patient_ids(self, patient_ids: Collection[str]) -> set[str]:
        known = {values["patient_id"] for values in self.stored.values()}
        known |= {patient.patient_id for patient in self.patients}
        return set(patient_ids) & known

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        self.batches.append(len(values))
        return insert_ignoring_existing(self.stored, values)


def make_history_event(patient: Patient, **overrides: object) -> PatientHistory:
    """Un événement fictif, lié au patient par son `patient_id`."""
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "patient_id": patient.patient_id,
        "kind": HistoryKind.GRAFT,
        "title": "Greffe rénale",
        "detail": "Donneur décédé · ABO compatible · exemple fictif",
        "occurred_on": date(2015, 8, 18),
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    return PatientHistory(**(values | overrides))


class FakeSerumTestRepository:
    """Remplace SerumTestRepository (même principe que FakePatientRepository)."""

    def __init__(self) -> None:
        self.stored: dict[uuid.UUID, Mapping[str, object]] = {}
        self.batches: list[int] = []

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        self.batches.append(len(values))
        return insert_ignoring_existing(self.stored, values)


class FakePatientHistoryRepository:
    """Remplace PatientHistoryRepository (même principe que FakePatientRepository)."""

    def __init__(self) -> None:
        self.stored: dict[uuid.UUID, Mapping[str, object]] = {}
        self.batches: list[int] = []

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        self.batches.append(len(values))
        return insert_ignoring_existing(self.stored, values)


class FakeSyntheticPatientRepository:
    """Remplace SyntheticPatientRepository (même principe que FakePatientRepository)."""

    def __init__(self, synthetic_patients: list[SyntheticPatient] | None = None) -> None:
        self.synthetic_patients: list[SyntheticPatient] = synthetic_patients or []
        self.total: int | None = None
        self.last_criteria: SyntheticPatientCriteria | None = None
        self.stored: dict[uuid.UUID, Mapping[str, object]] = {}
        self.batches: list[int] = []

    async def find(
        self, criteria: SyntheticPatientCriteria
    ) -> tuple[list[SyntheticPatient], int]:
        self.last_criteria = criteria
        total = len(self.synthetic_patients) if self.total is None else self.total
        return self.synthetic_patients, total

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        self.batches.append(len(values))
        return insert_ignoring_existing(self.stored, values)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def user_db() -> FakeUserDatabase:
    return FakeUserDatabase()


@pytest.fixture
def access_token_db() -> FakeAccessTokenDatabase:
    return FakeAccessTokenDatabase()


@pytest.fixture
def make_client(
    user_db: FakeUserDatabase, access_token_db: FakeAccessTokenDatabase
) -> Iterator[Callable[[], TestClient]]:
    """Fabrique des clients HTTP indépendants (chacun a son propre cookie) sur les mêmes faux."""
    app.dependency_overrides[get_user_db] = lambda: user_db
    app.dependency_overrides[get_access_token_db] = lambda: access_token_db
    yield lambda: TestClient(app, base_url=TEST_BASE_URL)
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client: Callable[[], TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def valid_password() -> str:
    return "p" * PASSWORD_MIN_LENGTH


@pytest.fixture
def credentials(valid_password: str) -> dict[str, str]:
    return {"email": "alice@example.com", "password": valid_password}


@pytest.fixture
def registered_user(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    """Un utilisateur inscrit via l'API (sans être connecté)."""
    response = client.post(f"{AUTH_URL}/register", json=credentials)
    assert response.status_code == 201
    return credentials
