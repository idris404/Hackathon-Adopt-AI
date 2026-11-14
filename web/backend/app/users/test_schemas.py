import uuid

import pytest
from pydantic import ValidationError

from app.constants.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.users.schemas import UserCreate, UserRead, UserUpdate

EMAIL = "alice@example.com"


@pytest.mark.parametrize("length", [PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH])
def test_user_create_accepts_password_at_the_bounds(length: int) -> None:
    user = UserCreate(email=EMAIL, password="p" * length)

    assert len(user.password) == length


@pytest.mark.parametrize("length", [PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1])
def test_user_create_rejects_password_outside_the_bounds(length: int) -> None:
    with pytest.raises(ValidationError):
        UserCreate(email=EMAIL, password="p" * length)


@pytest.mark.parametrize("email", ["", "not-an-email", "alice@", "@example.com"])
def test_user_create_rejects_malformed_email(email: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(email=email, password="p" * PASSWORD_MIN_LENGTH)


def test_user_update_allows_leaving_the_password_unchanged() -> None:
    update = UserUpdate(email=EMAIL)

    assert update.password is None


@pytest.mark.parametrize("length", [PASSWORD_MIN_LENGTH - 1, PASSWORD_MAX_LENGTH + 1])
def test_user_update_rejects_password_outside_the_bounds(length: int) -> None:
    with pytest.raises(ValidationError):
        UserUpdate(password="p" * length)


def test_user_read_exposes_no_password_field() -> None:
    assert "password" not in UserRead.model_fields
    assert "hashed_password" not in UserRead.model_fields


def test_user_read_drops_hashed_password_when_serializing_an_entity() -> None:
    class Entity:
        id = uuid.uuid4()
        email = EMAIL
        hashed_password = "$argon2id$secret"
        is_active = True
        is_superuser = False
        is_verified = False

    dumped = UserRead.model_validate(Entity()).model_dump()

    assert "hashed_password" not in dumped
