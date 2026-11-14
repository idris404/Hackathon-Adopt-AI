import pytest

from app.constants.database import ASYNC_DB_DRIVER, DEFAULT_DB_HOST
from app.constants.http import DEFAULT_FRONTEND_URL
from app.core.config import SeedSettings, Settings

DB_FIELDS = {"db_user": "adopt_ai", "db_password": "p@ss/word:1", "db_name": "adopt_ai_db", "db_port": 5432}


def build_settings(**overrides: object) -> Settings:
    # `_env_file=None` : on ne lit ni web/.env ni le fichier de la machine.
    return Settings(_env_file=None, **{**DB_FIELDS, **overrides})  # type: ignore[arg-type]


def test_database_url_uses_the_async_driver_and_escapes_special_characters() -> None:
    url = build_settings().database_url

    assert url.drivername == ASYNC_DB_DRIVER
    assert url.password == DB_FIELDS["db_password"]
    rendered = url.render_as_string(hide_password=False)
    assert DB_FIELDS["db_password"] not in rendered
    assert rendered.startswith(f"{ASYNC_DB_DRIVER}://{DB_FIELDS['db_user']}:")


def test_optional_settings_fall_back_to_the_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    settings = build_settings()

    assert settings.db_host == DEFAULT_DB_HOST
    assert settings.frontend_url == DEFAULT_FRONTEND_URL


def test_session_cookie_is_secure_unless_explicitly_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COOKIE_SECURE", raising=False)

    assert build_settings().cookie_secure is True
    assert build_settings(cookie_secure=False).cookie_secure is False


def test_the_password_is_not_exposed_when_printing_the_settings() -> None:
    assert DB_FIELDS["db_password"] not in repr(build_settings())


def test_missing_database_settings_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DB_USER", "DB_PASSWORD", "DB_NAME", "DB_PORT"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_the_api_settings_never_load_the_seed_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Le mot de passe du seed ne doit pas vivre dans le processus de l'API.
    monkeypatch.setenv("SEED_USER_EMAIL", "demo@example.com")
    monkeypatch.setenv("SEED_USER_PASSWORD", "p" * 12)

    settings = build_settings()

    assert not hasattr(settings, "seed_user_password")
    assert "seed_user" not in repr(settings)


def test_the_seed_password_is_not_exposed_when_printing_the_seed_settings() -> None:
    secret = "an-unprintable-secret"
    settings = SeedSettings(_env_file=None, seed_user_email="demo@example.com", seed_user_password=secret)  # type: ignore[arg-type]

    assert secret not in repr(settings)
