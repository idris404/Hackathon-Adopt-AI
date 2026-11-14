from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.constants.auth import PASSWORD_MAX_LENGTH


class LoginRequest(BaseModel):
    """Entrée de la connexion. Pas de longueur minimale : elle ne concerne que la création du mot
    de passe. La longueur maximale évite qu'un mot de passe géant serve à saturer le CPU (Argon2)."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
