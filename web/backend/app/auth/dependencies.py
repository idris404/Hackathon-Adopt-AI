import uuid
from collections.abc import AsyncIterator

from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.entity import AccessToken
from app.auth.repository import AccessTokenRepository
from app.auth.services import AuthService, SessionService
from app.constants.auth import (
    AUTH_BACKEND_NAME,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH,
    SESSION_COOKIE_SAMESITE,
    SESSION_LIFETIME_SECONDS,
)
from app.core.config import get_settings
from app.core.database import get_async_session
from app.users.dependencies import get_user_manager
from app.users.entity import User
from app.users.services import UserManager


async def get_access_token_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncIterator[AccessTokenRepository]:
    yield AccessTokenRepository(session, AccessToken)


def get_database_strategy(
    access_token_db: AccessTokenRepository = Depends(get_access_token_db),
) -> DatabaseStrategy[User, uuid.UUID, AccessToken]:
    return DatabaseStrategy(access_token_db, lifetime_seconds=SESSION_LIFETIME_SECONDS)


def get_auth_service(
    user_manager: UserManager = Depends(get_user_manager),
    strategy: DatabaseStrategy[User, uuid.UUID, AccessToken] = Depends(get_database_strategy),
) -> AuthService:
    return AuthService(user_manager, strategy)


def get_session_service(
    access_token_db: AccessTokenRepository = Depends(get_access_token_db),
) -> SessionService:
    return SessionService(access_token_db)


# Cookie HttpOnly, sans `domain` (limité à l'hôte de l'API), `Secure` selon l'environnement.
cookie_transport = CookieTransport(
    cookie_name=SESSION_COOKIE_NAME,
    cookie_max_age=SESSION_LIFETIME_SECONDS,
    cookie_path=SESSION_COOKIE_PATH,
    cookie_secure=get_settings().cookie_secure,
    cookie_httponly=SESSION_COOKIE_HTTPONLY,
    cookie_samesite=SESSION_COOKIE_SAMESITE,
)

auth_backend = AuthenticationBackend(
    name=AUTH_BACKEND_NAME,
    transport=cookie_transport,
    get_strategy=get_database_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dépendance unique pour protéger une route : `user: User = Depends(current_active_user)`.
current_active_user = fastapi_users.current_user(active=True)

# Idem, mais renvoie aussi le jeton de la session courante (déconnexion de l'appareil).
current_user_and_token = fastapi_users.authenticator.current_user_token(active=True)
