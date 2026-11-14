from fastapi import APIRouter

from app.auth.dependencies import fastapi_users
from app.constants.users import USERS_ROUTER_PREFIX, USERS_ROUTER_TAG
from app.users.schemas import UserRead, UserUpdate

router = APIRouter(prefix=USERS_ROUTER_PREFIX, tags=[USERS_ROUTER_TAG])

# GET et PATCH /users/me ; GET, PATCH et DELETE /users/{id} réservés aux superutilisateurs
router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))
