import uuid

from sqlalchemy import ColumnElement, Select, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.signatures import SIGN_QUEUE_MAX_HISTORY_EVENTS, SIGN_QUEUE_PROFILE
from app.patient_history.entity import PatientHistory
from app.patients.entity import Patient
from app.serum_tests.entity import SerumTest
from app.signatures.entity import PatientSignature
from app.signatures.exceptions import PatientAlreadySignedError

# Nombre d'événements d'historique du patient : sert de filtre et de premier critère de tri.
_HISTORY_COUNT = (
    select(func.count(PatientHistory.id))
    .where(PatientHistory.patient_id == Patient.patient_id)
    .correlate(Patient)
    .scalar_subquery()
)


def _eligible_conditions() -> list[ColumnElement[bool]]:
    """Un cas simple pas encore signé : profil sérique constant, historique court."""
    return [
        exists().where(
            SerumTest.patient_id == Patient.patient_id, SerumTest.profile == SIGN_QUEUE_PROFILE
        ),
        _HISTORY_COUNT <= SIGN_QUEUE_MAX_HISTORY_EVENTS,
        ~exists().where(PatientSignature.patient_id == Patient.patient_id),
    ]


class SignatureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def eligible(self, limit: int) -> list[Patient]:
        """Les premiers cas à signer : les historiques les plus courts d'abord, ordre stable."""
        query: Select[tuple[Patient]] = (
            select(Patient)
            .where(*_eligible_conditions())
            .options(selectinload(Patient.serum_tests), selectinload(Patient.history))
            .order_by(_HISTORY_COUNT, Patient.patient_id)
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def count_eligible(self) -> int:
        total = await self._session.scalar(
            select(func.count()).select_from(Patient).where(*_eligible_conditions())
        )
        return total or 0

    async def add(self, patient_id: str, user_id: uuid.UUID) -> PatientSignature:
        """Enregistre la signature. Une seconde signature du même patient est refusée."""
        signature = PatientSignature(patient_id=patient_id, signed_by=user_id)
        self._session.add(signature)
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise PatientAlreadySignedError from error
        await self._session.refresh(signature)
        return signature
