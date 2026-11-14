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

import uuid  # noqa: E402
from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from fastapi_users.db import BaseUserDatabase  # noqa: E402

from app.auth.dependencies import get_access_token_db  # noqa: E402
from app.constants.auth import AUTH_ROUTER_PREFIX, PASSWORD_MIN_LENGTH  # noqa: E402
from app.constants.http import API_V1_PREFIX  # noqa: E402
from app.constants.users import USERS_ROUTER_PREFIX  # noqa: E402
from app.main import app  # noqa: E402
from app.users.dependencies import get_user_db  # noqa: E402

# https : le cookie de session est `Secure`, le client de test ne le renvoie qu'en https.
TEST_BASE_URL = "https://testserver"

# URLs de l'API v1, construites comme main.py : version + préfixe du contexte.
AUTH_URL = f"{API_V1_PREFIX}{AUTH_ROUTER_PREFIX}"
USERS_URL = f"{API_V1_PREFIX}{USERS_ROUTER_PREFIX}"


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
