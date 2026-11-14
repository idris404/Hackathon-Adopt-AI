import pytest
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.exceptions import UserAlreadyExists
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.conftest import FakeUser, FakeUserDatabase
from app.core.security import build_password_helper
from app.users.schemas import UserCreate
from app.users.services import UserManager

EMAIL = "alice@example.com"

pytestmark = pytest.mark.anyio


@pytest.fixture
def manager(user_db: FakeUserDatabase) -> UserManager:
    return UserManager(user_db, build_password_helper())


def credentials(email: str, password: str) -> OAuth2PasswordRequestForm:
    return OAuth2PasswordRequestForm(username=email, password=password)


async def test_create_stores_an_argon2id_hash_and_never_the_password(
    manager: UserManager, valid_password: str
) -> None:
    user = await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)

    assert user.hashed_password != valid_password
    assert valid_password not in user.hashed_password
    assert user.hashed_password.startswith("$argon2id$")


async def test_create_rejects_duplicate_email(
    manager: UserManager, valid_password: str
) -> None:
    await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)

    with pytest.raises(UserAlreadyExists):
        await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)


async def test_create_rejects_duplicate_email_with_different_case(
    manager: UserManager, valid_password: str
) -> None:
    await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)

    with pytest.raises(UserAlreadyExists):
        await manager.create(
            UserCreate(email=EMAIL.upper(), password=valid_password), safe=True
        )


async def test_create_in_safe_mode_ignores_privileged_flags(
    manager: UserManager, valid_password: str
) -> None:
    payload = UserCreate(
        email=EMAIL, password=valid_password, is_superuser=True, is_verified=True
    )

    user = await manager.create(payload, safe=True)

    assert user.is_superuser is False
    assert user.is_verified is False


async def test_authenticate_returns_the_user_with_valid_credentials(
    manager: UserManager, valid_password: str
) -> None:
    created = await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)

    user = await manager.authenticate(credentials(EMAIL, valid_password))

    assert user is not None
    assert user.id == created.id


async def test_authenticate_returns_none_for_a_wrong_password(
    manager: UserManager, valid_password: str
) -> None:
    await manager.create(UserCreate(email=EMAIL, password=valid_password), safe=True)

    assert await manager.authenticate(credentials(EMAIL, valid_password + "x")) is None


async def test_authenticate_returns_none_for_an_unknown_email(
    manager: UserManager, valid_password: str
) -> None:
    assert await manager.authenticate(credentials("ghost@example.com", valid_password)) is None


async def test_authenticate_rehashes_a_password_stored_with_weaker_parameters(
    manager: UserManager, user_db: FakeUserDatabase, valid_password: str
) -> None:
    weak_hasher = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),))
    old_hash = weak_hasher.hash(valid_password)
    user = await user_db.create({"email": EMAIL, "hashed_password": old_hash})

    authenticated = await manager.authenticate(credentials(EMAIL, valid_password))

    assert authenticated is not None
    stored: FakeUser = user_db.users[user.id]
    assert stored.hashed_password != old_hash
    assert await manager.authenticate(credentials(EMAIL, valid_password)) is not None
