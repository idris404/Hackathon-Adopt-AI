from collections.abc import Mapping, Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.serum_tests.entity import SerumTest


class SerumTestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        """Insère les tests dont l'id est absent ; renvoie le nombre réellement insérés.

        Leur `patient_id` doit être celui d'un patient existant (clé étrangère).
        """
        result = await self._session.execute(
            insert(SerumTest).values(list(values)).on_conflict_do_nothing()
        )
        return result.rowcount
