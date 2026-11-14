from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.synthetic_patients.repository import SyntheticPatientRepository
from app.synthetic_patients.services import SyntheticPatientService


def get_synthetic_patient_service(
    session: AsyncSession = Depends(get_async_session),
) -> SyntheticPatientService:
    return SyntheticPatientService(SyntheticPatientRepository(session))
