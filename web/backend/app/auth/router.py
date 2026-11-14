import uuid

from fastapi import APIRouter, Depends, Response, status
from fastapi_users.authentication.strategy.db import DatabaseStrategy

from app.auth.dependencies import (
    auth_backend,
    current_active_user,
    current_user_and_token,
    fastapi_users,
    get_auth_service,
    get_session_service,
)
from app.auth.entity import AccessToken
from app.auth.schemas import LoginRequest
from app.auth.services import AuthService, SessionService
from app.constants.auth import AUTH_ROUTER_PREFIX, AUTH_ROUTER_TAG
from app.users.entity import User
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix=AUTH_ROUTER_PREFIX, tags=[AUTH_ROUTER_TAG])

# POST /auth/register
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))

UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing token or inactive user."}
}


@router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Invalid credentials."}},
)
async def login(
    credentials: LoginRequest, service: AuthService = Depends(get_auth_service)
) -> Response:
    """Connexion : corps JSON `{email, password}`. La session est posée dans un cookie HttpOnly."""
    token = await service.login(credentials.email, credentials.password)
    return await auth_backend.transport.get_login_response(token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=UNAUTHORIZED_RESPONSE,
)
async def logout(
    user_and_token: tuple[User, str] = Depends(current_user_and_token),
    strategy: DatabaseStrategy[User, uuid.UUID, AccessToken] = Depends(
        auth_backend.get_strategy
    ),
) -> Response:
    """Déconnexion de l'appareil courant : supprime cette session côté serveur."""
    user, token = user_and_token
    return await auth_backend.logout(strategy, user, token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=UNAUTHORIZED_RESPONSE,
)
async def logout_all(
    user: User = Depends(current_active_user),
    service: SessionService = Depends(get_session_service),
) -> Response:
    """Déconnexion de tous les appareils : révoque toutes les sessions de l'utilisateur."""
    await service.logout_all(user.id)
    return await auth_backend.transport.get_logout_response()
