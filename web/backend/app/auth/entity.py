from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID

from app.core.database import Base


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    """Table `accesstoken` : une ligne par session ouverte (jeton opaque, user_id, created_at).

    Supprimer la ligne révoque la session.
    """
