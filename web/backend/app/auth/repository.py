import uuid

from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from sqlalchemy import delete

from app.auth.entity import AccessToken


class AccessTokenRepository(SQLAlchemyAccessTokenDatabase[AccessToken]):
    """Accès aux sessions : l'adaptateur de FastAPI Users (lecture, création, suppression d'un
    jeton) complété par la suppression de toutes les sessions d'un utilisateur.

    Comme l'adaptateur de la librairie, chaque opération valide sa transaction.
    """

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(self.access_token_table).where(
                self.access_token_table.user_id == user_id
            )
        )
        await self.session.commit()
