from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

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


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # les champs requis viennent de l'environnement
