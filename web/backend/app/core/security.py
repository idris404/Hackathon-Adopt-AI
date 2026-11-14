from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.constants.auth import (
    ARGON2_MEMORY_COST_KIB,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
)


def build_password_helper() -> PasswordHelper:
    """Argon2id uniquement, paramètres explicites.

    Un hash produit avec d'anciens paramètres est recalculé à la prochaine
    connexion réussie (`verify_and_update`).
    """
    hasher = Argon2Hasher(
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST_KIB,
        parallelism=ARGON2_PARALLELISM,
    )
    return PasswordHelper(PasswordHash((hasher,)))
