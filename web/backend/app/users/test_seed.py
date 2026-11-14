import pytest
from pydantic import SecretStr

from app.conftest import FakeUserDatabase
from app.constants.auth import PASSWORD_MIN_LENGTH
from app.constants.seed import SEED_USER_IS_SUPERUSER, SEED_USER_IS_VERIFIED
from app.core.config import SeedSettings
from app.core.exceptions import SeedError
from app.core.security import build_password_helper
from app.users.schemas import UserCreate
from app.users.seed import DemoUser, UserSeedReport, load_demo_user, seed_users
from app.users.services import UserManager

pytestmark = pytest.mark.anyio

DEMO_EMAIL = "demo@example.com"


@pytest.fixture
def manager(user_db: FakeUserDatabase) -> UserManager:
    return UserManager(user_db, build_password_helper())


@pytest.fixture
def demo_user(valid_password: str) -> DemoUser:
    return DemoUser(DEMO_EMAIL, SecretStr(valid_password))


async def test_seed_creates_the_demo_account(
    manager: UserManager, user_db: FakeUserDatabase, demo_user: DemoUser
) -> None:
    report = await seed_users(manager, demo_user)

    assert report == UserSeedReport(created=True)
    user = await user_db.get_by_email(DEMO_EMAIL)
    assert user is not None
    assert user.is_active is True
    assert user.is_superuser is SEED_USER_IS_SUPERUSER
    assert user.is_verified is SEED_USER_IS_VERIFIED


async def test_seed_stores_an_argon2id_hash_and_never_the_password(
    manager: UserManager,
    user_db: FakeUserDatabase,
    demo_user: DemoUser,
    valid_password: str,
) -> None:
    await seed_users(manager, demo_user)

    user = await user_db.get_by_email(DEMO_EMAIL)
    assert user is not None
    assert user.hashed_password.startswith("$argon2id$")
    assert valid_password not in user.hashed_password


async def test_the_demo_account_can_log_in_with_the_configured_credentials(
    manager: UserManager, demo_user: DemoUser, valid_password: str
) -> None:
    await seed_users(manager, demo_user)

    user = await manager.authenticate_with_email(DEMO_EMAIL, valid_password)

    assert user is not None
    assert user.email == DEMO_EMAIL


async def test_replaying_the_seed_changes_nothing(
    manager: UserManager, user_db: FakeUserDatabase, demo_user: DemoUser
) -> None:
    await seed_users(manager, demo_user)
    first = await user_db.get_by_email(DEMO_EMAIL)
    assert first is not None
    first_id, first_hash = first.id, first.hashed_password

    report = await seed_users(manager, demo_user)

    assert report == UserSeedReport(created=False)
    assert len(user_db.users) == 1
    kept = await user_db.get_by_email(DEMO_EMAIL)
    assert kept is not None
    assert (kept.id, kept.hashed_password) == (first_id, first_hash)


async def test_an_existing_account_keeps_its_own_password(
    manager: UserManager, valid_password: str
) -> None:
    # Même email, autre mot de passe : le seed ne doit ni l'écraser ni le remplacer.
    other_password = "q" * PASSWORD_MIN_LENGTH
    await manager.create(UserCreate(email=DEMO_EMAIL, password=other_password), safe=True)

    report = await seed_users(manager, DemoUser(DEMO_EMAIL, SecretStr(valid_password)))

    assert report == UserSeedReport(created=False)
    assert await manager.authenticate_with_email(DEMO_EMAIL, other_password) is not None
    assert await manager.authenticate_with_email(DEMO_EMAIL, valid_password) is None


# --- lecture du compte dans l'environnement (web/.env) -------------------------------------


@pytest.fixture
def no_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ni web/.env ni le fichier de la machine : seules les variables posées par le test comptent."""
    monkeypatch.setitem(SeedSettings.model_config, "env_file", None)
    monkeypatch.delenv("SEED_USER_EMAIL", raising=False)
    monkeypatch.delenv("SEED_USER_PASSWORD", raising=False)


@pytest.mark.usefixtures("no_env_file")
def test_the_demo_account_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, valid_password: str
) -> None:
    monkeypatch.setenv("SEED_USER_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("SEED_USER_PASSWORD", valid_password)

    demo_user = load_demo_user()

    assert demo_user.email == DEMO_EMAIL
    assert demo_user.password.get_secret_value() == valid_password


@pytest.mark.usefixtures("no_env_file")
def test_a_missing_variable_stops_the_seed_with_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEED_USER_EMAIL", DEMO_EMAIL)  # le mot de passe manque

    with pytest.raises(SeedError, match="SEED_USER_PASSWORD"):
        load_demo_user()


@pytest.mark.usefixtures("no_env_file")
def test_an_invalid_password_is_rejected_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    too_short = "s" * (PASSWORD_MIN_LENGTH - 1)
    monkeypatch.setenv("SEED_USER_EMAIL", DEMO_EMAIL)
    monkeypatch.setenv("SEED_USER_PASSWORD", too_short)

    with pytest.raises(SeedError) as error:
        load_demo_user()

    assert too_short not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__


@pytest.mark.usefixtures("no_env_file")
def test_an_invalid_email_is_rejected(
    monkeypatch: pytest.MonkeyPatch, valid_password: str
) -> None:
    monkeypatch.setenv("SEED_USER_EMAIL", "not-an-email")
    monkeypatch.setenv("SEED_USER_PASSWORD", valid_password)

    with pytest.raises(SeedError):
        load_demo_user()


def test_the_password_is_hidden_when_printing_the_demo_user(valid_password: str) -> None:
    assert valid_password not in repr(DemoUser(DEMO_EMAIL, SecretStr(valid_password)))
