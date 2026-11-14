from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.patients.repository import PatientRepository
from app.patients.services import PatientService


def get_patient_service(session: AsyncSession = Depends(get_async_session)) -> PatientService:
    return PatientService(PatientRepository(session))
