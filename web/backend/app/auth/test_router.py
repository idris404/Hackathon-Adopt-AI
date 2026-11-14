from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from fastapi_users.router.common import ErrorCode

from app.conftest import AUTH_URL, USERS_URL, FakeAccessTokenDatabase, FakeUserDatabase
from app.constants.auth import (
    INVALID_CREDENTIALS_CODE,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME_SECONDS,
)

REGISTER_URL = f"{AUTH_URL}/register"
LOGIN_URL = f"{AUTH_URL}/login"
LOGOUT_URL = f"{AUTH_URL}/logout"
LOGOUT_ALL_URL = f"{AUTH_URL}/logout-all"
ME_URL = f"{USERS_URL}/me"

PUBLIC_USER_FIELDS = {"id", "email", "is_active", "is_superuser", "is_verified"}


def login(client: TestClient, email: str, password: str):
    return client.post(LOGIN_URL, json={"email": email, "password": password})


# --- Inscription -----------------------------------------------------------------


def test_register_creates_the_user_and_returns_only_public_fields(
    client: TestClient, credentials: dict[str, str], user_db: FakeUserDatabase
) -> None:
    response = client.post(REGISTER_URL, json=credentials)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == PUBLIC_USER_FIELDS
    assert body["email"] == credentials["email"]
    assert len(user_db.users) == 1


def test_register_never_stores_the_password_in_clear(
    client: TestClient, credentials: dict[str, str], user_db: FakeUserDatabase
) -> None:
    client.post(REGISTER_URL, json=credentials)

    stored = next(iter(user_db.users.values()))
    assert stored.hashed_password != credentials["password"]
    assert credentials["password"] not in stored.hashed_password


def test_register_rejects_an_email_already_used(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = client.post(REGISTER_URL, json=registered_user)

    assert response.status_code == 400
    assert response.json() == {"detail": ErrorCode.REGISTER_USER_ALREADY_EXISTS}


def test_register_rejects_an_email_already_used_with_a_different_case(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    payload = {**registered_user, "email": registered_user["email"].upper()}

    response = client.post(REGISTER_URL, json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": ErrorCode.REGISTER_USER_ALREADY_EXISTS}


@pytest.mark.parametrize("length", [PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1])
def test_register_rejects_a_password_outside_the_bounds(
    client: TestClient, user_db: FakeUserDatabase, length: int
) -> None:
    response = client.post(
        REGISTER_URL, json={"email": "alice@example.com", "password": "p" * length}
    )

    assert response.status_code == 422
    assert user_db.users == {}


def test_register_rejects_a_malformed_email(
    client: TestClient, valid_password: str
) -> None:
    response = client.post(
        REGISTER_URL, json={"email": "not-an-email", "password": valid_password}
    )

    assert response.status_code == 422


def test_register_cannot_grant_privileges(
    client: TestClient, credentials: dict[str, str], user_db: FakeUserDatabase
) -> None:
    payload = {**credentials, "is_superuser": True, "is_verified": True}

    response = client.post(REGISTER_URL, json=payload)

    assert response.status_code == 201
    assert response.json()["is_superuser"] is False
    assert response.json()["is_verified"] is False
    stored = next(iter(user_db.users.values()))
    assert stored.is_superuser is False
    assert stored.is_verified is False


# --- Connexion -------------------------------------------------------------------


def test_login_opens_a_session_stored_in_an_http_only_cookie(
    client: TestClient,
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    response = login(client, registered_user["email"], registered_user["password"])

    assert response.status_code == 204
    assert response.content == b""
    assert len(access_token_db.tokens) == 1
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert f"max-age={SESSION_LIFETIME_SECONDS}" in cookie
    assert "path=/" in cookie
    assert "domain" not in cookie


def test_login_cookie_is_not_the_password_nor_a_user_identifier(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = login(client, registered_user["email"], registered_user["password"])

    token = response.cookies[SESSION_COOKIE_NAME]
    assert registered_user["password"] not in token
    assert registered_user["email"] not in token


def test_login_issues_a_new_session_token_every_time(
    client: TestClient,
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    first = login(client, registered_user["email"], registered_user["password"])
    second = login(client, registered_user["email"], registered_user["password"])

    assert first.cookies[SESSION_COOKIE_NAME] != second.cookies[SESSION_COOKIE_NAME]
    assert len(access_token_db.tokens) == 2


def test_login_gives_the_same_error_for_unknown_email_and_wrong_password(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    unknown_email = login(client, "ghost@example.com", registered_user["password"])
    wrong_password = login(
        client, registered_user["email"], registered_user["password"] + "x"
    )

    assert unknown_email.status_code == wrong_password.status_code == 400
    assert unknown_email.json() == wrong_password.json()
    assert unknown_email.json() == {"detail": INVALID_CREDENTIALS_CODE}
    assert SESSION_COOKIE_NAME not in unknown_email.cookies
    assert SESSION_COOKIE_NAME not in wrong_password.cookies


def test_login_rejects_an_inactive_account_with_the_same_error(
    client: TestClient, registered_user: dict[str, str], user_db: FakeUserDatabase
) -> None:
    next(iter(user_db.users.values())).is_active = False

    response = login(client, registered_user["email"], registered_user["password"])

    assert response.status_code == 400
    assert response.json() == {"detail": INVALID_CREDENTIALS_CODE}


def test_login_requires_both_fields(client: TestClient) -> None:
    response = client.post(LOGIN_URL, json={"email": "alice@example.com"})

    assert response.status_code == 422


def test_login_expects_email_and_not_username(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    payload = {"username": registered_user["email"], "password": registered_user["password"]}

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422


def test_login_does_not_accept_a_form_body(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    form = {"username": registered_user["email"], "password": registered_user["password"]}

    response = client.post(LOGIN_URL, data=form)

    assert response.status_code == 422
    assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.parametrize("email", ["", "not-an-email", "alice@"])
def test_login_rejects_a_malformed_email(
    client: TestClient, valid_password: str, email: str
) -> None:
    assert login(client, email, valid_password).status_code == 422


def test_login_rejects_a_password_longer_than_the_maximum_without_hashing_it(
    client: TestClient, registered_user: dict[str, str], access_token_db: FakeAccessTokenDatabase
) -> None:
    response = login(client, registered_user["email"], "p" * (PASSWORD_MAX_LENGTH + 1))

    assert response.status_code == 422
    assert access_token_db.tokens == {}


def test_login_accepts_the_email_in_any_case(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = login(client, registered_user["email"].upper(), registered_user["password"])

    assert response.status_code == 204


# --- Session ---------------------------------------------------------------------


def test_a_logged_in_client_can_reach_a_protected_route(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    login(client, registered_user["email"], registered_user["password"])

    response = client.get(ME_URL)

    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]


def test_a_protected_route_rejects_a_missing_session(client: TestClient) -> None:
    assert client.get(ME_URL).status_code == 401


def test_a_protected_route_rejects_a_forged_session_token(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "forged-token")

    assert client.get(ME_URL).status_code == 401


def test_a_session_older_than_its_lifetime_is_rejected(
    client: TestClient,
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    login(client, registered_user["email"], registered_user["password"])
    session = next(iter(access_token_db.tokens.values()))
    session.created_at = datetime.now(timezone.utc) - timedelta(
        seconds=SESSION_LIFETIME_SECONDS + 1
    )

    assert client.get(ME_URL).status_code == 401


def test_a_session_of_a_deactivated_account_is_rejected(
    client: TestClient, registered_user: dict[str, str], user_db: FakeUserDatabase
) -> None:
    login(client, registered_user["email"], registered_user["password"])
    next(iter(user_db.users.values())).is_active = False

    assert client.get(ME_URL).status_code == 401


def test_a_session_of_a_deleted_account_is_rejected(
    client: TestClient, registered_user: dict[str, str], user_db: FakeUserDatabase
) -> None:
    login(client, registered_user["email"], registered_user["password"])
    user_db.users.clear()

    assert client.get(ME_URL).status_code == 401


def test_two_clients_have_independent_sessions(
    make_client: Callable[[], TestClient],
    registered_user: dict[str, str],
) -> None:
    alice, anonymous = make_client(), make_client()
    login(alice, registered_user["email"], registered_user["password"])

    assert alice.get(ME_URL).status_code == 200
    assert anonymous.get(ME_URL).status_code == 401


# --- Déconnexion -----------------------------------------------------------------


def test_logout_revokes_the_session_on_the_server(
    make_client: Callable[[], TestClient],
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    client, attacker = make_client(), make_client()
    login_response = login(client, registered_user["email"], registered_user["password"])
    stolen_token = login_response.cookies[SESSION_COOKIE_NAME]

    response = client.post(LOGOUT_URL)

    assert response.status_code == 204
    assert access_token_db.tokens == {}
    # Même en rejouant l'ancien cookie, la session n'existe plus côté serveur.
    attacker.cookies.set(SESSION_COOKIE_NAME, stolen_token)
    assert attacker.get(ME_URL).status_code == 401


def test_logout_clears_the_cookie_in_the_browser(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    login(client, registered_user["email"], registered_user["password"])

    response = client.post(LOGOUT_URL)

    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get(ME_URL).status_code == 401


def test_logout_only_ends_the_current_session(
    make_client: Callable[[], TestClient],
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    laptop, phone = make_client(), make_client()
    login(laptop, registered_user["email"], registered_user["password"])
    login(phone, registered_user["email"], registered_user["password"])

    laptop.post(LOGOUT_URL)

    assert laptop.get(ME_URL).status_code == 401
    assert phone.get(ME_URL).status_code == 200
    assert len(access_token_db.tokens) == 1


def test_logout_requires_an_authenticated_session(client: TestClient) -> None:
    assert client.post(LOGOUT_URL).status_code == 401


# --- Déconnexion de tous les appareils -------------------------------------------


def test_logout_all_revokes_the_sessions_of_every_device(
    make_client: Callable[[], TestClient],
    registered_user: dict[str, str],
    access_token_db: FakeAccessTokenDatabase,
) -> None:
    laptop, phone = make_client(), make_client()
    login(laptop, registered_user["email"], registered_user["password"])
    login(phone, registered_user["email"], registered_user["password"])
    assert len(access_token_db.tokens) == 2

    response = laptop.post(LOGOUT_ALL_URL)

    assert response.status_code == 204
    assert response.content == b""
    assert access_token_db.tokens == {}
    assert laptop.get(ME_URL).status_code == 401
    assert phone.get(ME_URL).status_code == 401


def test_logout_all_clears_the_cookie_of_the_calling_device(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    login(client, registered_user["email"], registered_user["password"])

    response = client.post(LOGOUT_ALL_URL)

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "max-age=0" in cookie


def test_logout_all_does_not_end_the_sessions_of_other_users(
    make_client: Callable[[], TestClient], valid_password: str
) -> None:
    alice, bob = make_client(), make_client()
    for client, email in ((alice, "alice@example.com"), (bob, "bob@example.com")):
        client.post(REGISTER_URL, json={"email": email, "password": valid_password})
        login(client, email, valid_password)

    alice.post(LOGOUT_ALL_URL)

    assert alice.get(ME_URL).status_code == 401
    assert bob.get(ME_URL).status_code == 200


def test_logout_all_requires_an_authenticated_session(client: TestClient) -> None:
    assert client.post(LOGOUT_ALL_URL).status_code == 401


def test_logout_all_rejects_a_forged_session_token(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "forged-token")

    assert client.post(LOGOUT_ALL_URL).status_code == 401
