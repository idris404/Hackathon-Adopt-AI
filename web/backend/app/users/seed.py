"""Ingestion du compte de démonstration (table `user`).

Étape `users` du seed (`python -m app.seed`). L'email et le mot de passe viennent de web/.env
(`SEED_USER_EMAIL`, `SEED_USER_PASSWORD`), jamais du code. Le compte passe par `UserManager.create` :
le mot de passe est haché en Argon2id comme à l'inscription, jamais stocké ni affiché en clair.
Rejouable : si l'email existe déjà, rien n'est modifié (le mot de passe d'un compte existant n'est
pas écrasé).
"""

from dataclasses import dataclass

from fastapi_users.exceptions import UserAlreadyExists
from pydantic import SecretStr, ValidationError

from app.constants.seed import (
    SEED_USER_ENV_ERROR,
    SEED_USER_IS_SUPERUSER,
    SEED_USER_IS_VERIFIED,
)
from app.core.config import SeedSettings
from app.core.exceptions import SeedError
from app.users.schemas import UserCreate
from app.users.services import UserManager


@dataclass(frozen=True)
class DemoUser:
    email: str
    password: SecretStr  # masqué dans `repr` : jamais dans un log ni une trace


@dataclass(frozen=True)
class UserSeedReport:
    created: bool  # False : le compte existait déjà


def load_demo_user() -> DemoUser:
    """Lit le compte de démonstration dans l'environnement (web/.env).

    Une valeur absente ou invalide devient une `SeedError` au message fixe : l'erreur de validation
    de Pydantic cite la valeur reçue, donc le mot de passe, et ne doit pas remonter jusqu'au terminal.
    """
    try:
        settings = SeedSettings()  # type: ignore[call-arg]  # les champs viennent de l'environnement
    except ValidationError:
        raise SeedError(SEED_USER_ENV_ERROR) from None
    return DemoUser(settings.seed_user_email, settings.seed_user_password)


async def seed_users(users: UserManager, demo_user: DemoUser) -> UserSeedReport:
    payload = UserCreate(
        email=demo_user.email,
        password=demo_user.password.get_secret_value(),
        is_superuser=SEED_USER_IS_SUPERUSER,
        is_verified=SEED_USER_IS_VERIFIED,
    )
    try:
        # `safe=False` : seule façon de poser is_superuser / is_verified. Réservé à ce seed, dont les
        # droits viennent de `constants/`, jamais d'une requête.
        await users.create(payload, safe=False)
    except UserAlreadyExists:
        return UserSeedReport(created=False)
    return UserSeedReport(created=True)
