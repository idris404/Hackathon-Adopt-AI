import uuid
from collections.abc import AsyncIterator

from fastapi import Depends
from fastapi_users.password import PasswordHelper
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import build_password_helper
from app.users.entity import User
from app.users.services import UserManager


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncIterator[SQLAlchemyUserDatabase[User, uuid.UUID]]:
    yield SQLAlchemyUserDatabase(session, User)


def get_password_helper() -> PasswordHelper:
    return build_password_helper()


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db),
    password_helper: PasswordHelper = Depends(get_password_helper),
) -> AsyncIterator[UserManager]:
    yield UserManager(user_db, password_helper)
