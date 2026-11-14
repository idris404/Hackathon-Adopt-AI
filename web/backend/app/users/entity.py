from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from app.core.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Table `user` : id (UUID), email unique, hashed_password, is_active, is_superuser, is_verified."""
