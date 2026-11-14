import uuid

from fastapi_users import schemas
from pydantic import Field

from app.constants.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Sortie : jamais de mot de passe ni de hash."""


class UserCreate(schemas.BaseUserCreate):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class UserUpdate(schemas.BaseUserUpdate):
    password: str | None = Field(
        default=None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
