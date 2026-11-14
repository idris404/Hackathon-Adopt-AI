import uuid

import pytest
from fastapi_users.authentication.strategy.db import DatabaseStrategy

from app.auth.exceptions import InvalidCredentialsError
from app.auth.services import AuthService, SessionService
from app.conftest import FakeAccessTokenDatabase, FakeUserDatabase
from app.constants.auth import SESSION_LIFETIME_SECONDS
from app.core.security import build_password_helper
from app.users.schemas import UserCreate
from app.users.services import UserManager

pytestmark = pytest.mark.anyio


@pytest.fixture
def service(access_token_db: FakeAccessTokenDatabase) -> SessionService:
    return SessionService(access_token_db)


async def open_session(
    access_token_db: FakeAccessTokenDatabase, user_id: uuid.UUID, token: str
) -> None:
    await access_token_db.create({"token": token, "user_id": user_id})


async def test_logout_all_revokes_every_session_of_the_user(
    service: SessionService, access_token_db: FakeAccessTokenDatabase
) -> None:
    user_id = uuid.uuid4()
    await open_session(access_token_db, user_id, "laptop")
    await open_session(access_token_db, user_id, "phone")

    await service.logout_all(user_id)

    assert access_token_db.tokens == {}


async def test_logout_all_keeps_the_sessions_of_other_users(
    service: SessionService, access_token_db: FakeAccessTokenDatabase
) -> None:
    user_id, other_user_id = uuid.uuid4(), uuid.uuid4()
    await open_session(access_token_db, user_id, "mine")
    await open_session(access_token_db, other_user_id, "theirs")

    await service.logout_all(user_id)

    assert set(access_token_db.tokens) == {"theirs"}


async def test_logout_all_without_any_session_does_nothing(
    service: SessionService, access_token_db: FakeAccessTokenDatabase
) -> None:
    await open_session(access_token_db, uuid.uuid4(), "theirs")

    await service.logout_all(uuid.uuid4())

    assert set(access_token_db.tokens) == {"theirs"}


# --- AuthService -----------------------------------------------------------------

EMAIL = "alice@example.com"


@pytest.fixture
def user_manager(user_db: FakeUserDatabase) -> UserManager:
    return UserManager(user_db, build_password_helper())


@pytest.fixture
def auth_service(
    user_manager: UserManager, access_token_db: FakeAccessTokenDatabase
) -> AuthService:
    strategy = DatabaseStrategy(access_token_db, lifetime_seconds=SESSION_LIFETIME_SECONDS)
    return AuthService(user_manager, strategy)


@pytest.fixture
async def alice(user_manager: UserManager, valid_password: str):
    return await user_manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)


async def test_login_opens_a_session_for_the_user(
    auth_service: AuthService,
    access_token_db: FakeAccessTokenDatabase,
    alice,
    valid_password: str,
) -> None:
    token = await auth_service.login(EMAIL, valid_password)

    assert access_token_db.tokens[token].user_id == alice.id


async def test_login_issues_a_different_token_each_time(
    auth_service: AuthService, alice, valid_password: str
) -> None:
    first = await auth_service.login(EMAIL, valid_password)
    second = await auth_service.login(EMAIL, valid_password)

    assert first != second


@pytest.mark.parametrize(
    ("email", "password_suffix"),
    [(EMAIL, "-wrong"), ("ghost@example.com", "")],
    ids=["wrong-password", "unknown-email"],
)
async def test_login_refuses_bad_credentials_and_opens_no_session(
    auth_service: AuthService,
    access_token_db: FakeAccessTokenDatabase,
    alice,
    valid_password: str,
    email: str,
    password_suffix: str,
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email, valid_password + password_suffix)

    assert access_token_db.tokens == {}


async def test_login_refuses_an_inactive_account_with_the_same_error(
    auth_service: AuthService,
    access_token_db: FakeAccessTokenDatabase,
    user_db: FakeUserDatabase,
    alice,
    valid_password: str,
) -> None:
    user_db.users[alice.id].is_active = False

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(EMAIL, valid_password)

    assert access_token_db.tokens == {}
