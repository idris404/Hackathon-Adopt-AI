from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.constants.auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.constants.database import ASYNC_DB_DRIVER, DEFAULT_DB_HOST
from app.constants.http import DEFAULT_FRONTEND_URL

# web/.env : config.py → core → app → backend → web
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    db_user: str
    db_password: SecretStr
    db_name: str
    db_port: int
    db_host: str = DEFAULT_DB_HOST

    frontend_url: str = DEFAULT_FRONTEND_URL
    # Sûr par défaut : mettre COOKIE_SECURE=false uniquement en développement local (HTTP).
    cookie_secure: bool = True

    @property
    def database_url(self) -> URL:
        return URL.create(
            ASYNC_DB_DRIVER,
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


class SeedSettings(BaseSettings):
    """Compte de démonstration du seed (`python -m app.seed`, étape `users`).

    Séparé de `Settings` : l'API n'en a pas besoin, elle ne charge donc jamais ce mot de passe, et une
    valeur invalide ici ne l'empêche pas de démarrer. Lue seulement par le seed, quand l'étape tourne.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    seed_user_email: EmailStr
    # Mêmes bornes que l'inscription : le compte doit pouvoir passer `UserCreate`.
    seed_user_password: SecretStr = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # les champs requis viennent de l'environnement
