from fastapi import APIRouter

from app.auth.dependencies import auth_backend, fastapi_users
from app.constants.auth import AUTH_ROUTER_PREFIX, AUTH_ROUTER_TAG
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix=AUTH_ROUTER_PREFIX, tags=[AUTH_ROUTER_TAG])

# POST /auth/login et POST /auth/logout
router.include_router(fastapi_users.get_auth_router(auth_backend))
# POST /auth/register
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
