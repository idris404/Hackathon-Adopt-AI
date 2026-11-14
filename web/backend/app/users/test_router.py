import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from fastapi_users.router.common import ErrorCode

from app.conftest import AUTH_URL, USERS_URL, FakeUser, FakeUserDatabase
from app.constants.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH

ME_URL = f"{USERS_URL}/me"
LOGIN_URL = f"{AUTH_URL}/login"
REGISTER_URL = f"{AUTH_URL}/register"

PUBLIC_USER_FIELDS = {"id", "email", "is_active", "is_superuser", "is_verified"}


def login(client: TestClient, email: str, password: str):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def find_user(user_db: FakeUserDatabase, email: str) -> FakeUser:
    return next(user for user in user_db.users.values() if user.email == email)


@pytest.fixture
def logged_in(client: TestClient, registered_user: dict[str, str]) -> TestClient:
    login(client, registered_user["email"], registered_user["password"])
    return client


def test_me_returns_the_current_user_without_any_secret(
    logged_in: TestClient, registered_user: dict[str, str]
) -> None:
    response = logged_in.get(ME_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PUBLIC_USER_FIELDS
    assert body["email"] == registered_user["email"]


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get(ME_URL).status_code == 401


def test_update_me_changes_the_password(
    logged_in: TestClient,
    make_client: Callable[[], TestClient],
    registered_user: dict[str, str],
) -> None:
    new_password = "n" * PASSWORD_MIN_LENGTH

    response = logged_in.patch(ME_URL, json={"password": new_password})

    assert response.status_code == 200
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()
    fresh = make_client()
    assert login(fresh, registered_user["email"], registered_user["password"]).status_code == 400
    assert login(fresh, registered_user["email"], new_password).status_code == 204


@pytest.mark.parametrize("length", [PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1])
def test_update_me_rejects_a_password_outside_the_bounds(
    logged_in: TestClient, length: int
) -> None:
    response = logged_in.patch(ME_URL, json={"password": "p" * length})

    assert response.status_code == 422


def test_update_me_cannot_grant_privileges(
    logged_in: TestClient, user_db: FakeUserDatabase
) -> None:
    response = logged_in.patch(
        ME_URL, json={"is_superuser": True, "is_verified": True, "is_active": False}
    )

    assert response.status_code == 200
    stored = next(iter(user_db.users.values()))
    assert stored.is_superuser is False
    assert stored.is_verified is False
    assert stored.is_active is True


def test_update_me_rejects_an_email_used_by_another_account(
    make_client: Callable[[], TestClient], valid_password: str
) -> None:
    alice, bob = make_client(), make_client()
    alice.post(REGISTER_URL, json={"email": "alice@example.com", "password": valid_password})
    bob.post(REGISTER_URL, json={"email": "bob@example.com", "password": valid_password})
    login(bob, "bob@example.com", valid_password)

    response = bob.patch(ME_URL, json={"email": "alice@example.com"})

    assert response.status_code == 400
    assert response.json() == {"detail": ErrorCode.UPDATE_USER_EMAIL_ALREADY_EXISTS}


def test_changing_the_email_resets_the_verified_flag(
    logged_in: TestClient, user_db: FakeUserDatabase
) -> None:
    next(iter(user_db.users.values())).is_verified = True

    logged_in.patch(ME_URL, json={"email": "new-address@example.com"})

    assert next(iter(user_db.users.values())).is_verified is False


def test_a_regular_user_cannot_read_another_account_by_id(
    logged_in: TestClient, user_db: FakeUserDatabase
) -> None:
    other = next(iter(user_db.users.values()))

    response = logged_in.get(f"{USERS_URL}/{other.id}")

    assert response.status_code == 403


def test_a_regular_user_cannot_delete_an_account(
    logged_in: TestClient, user_db: FakeUserDatabase
) -> None:
    response = logged_in.delete(f"{USERS_URL}/{uuid.uuid4()}")

    assert response.status_code == 403
    assert len(user_db.users) == 1


def test_a_superuser_can_read_another_account_by_id(
    make_client: Callable[[], TestClient], user_db: FakeUserDatabase, valid_password: str
) -> None:
    admin, member = make_client(), make_client()
    admin.post(REGISTER_URL, json={"email": "admin@example.com", "password": valid_password})
    member.post(REGISTER_URL, json={"email": "member@example.com", "password": valid_password})
    admin_user = find_user(user_db, "admin@example.com")
    admin_user.is_superuser = True
    login(admin, "admin@example.com", valid_password)
    member_id = find_user(user_db, "member@example.com").id

    response = admin.get(f"{USERS_URL}/{member_id}")

    assert response.status_code == 200
    assert response.json()["email"] == "member@example.com"
    assert set(response.json()) == PUBLIC_USER_FIELDS
