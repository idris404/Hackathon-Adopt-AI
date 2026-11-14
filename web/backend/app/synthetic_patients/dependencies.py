from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.patients.dependencies import get_patient_service
from app.patients.services import PatientService
from app.synthetic_patients.repository import SyntheticPatientRepository
from app.synthetic_patients.services import SyntheticPatientService


def get_synthetic_patient_service(
    session: AsyncSession = Depends(get_async_session),
    patients: PatientService = Depends(get_patient_service),
) -> SyntheticPatientService:
    return SyntheticPatientService(SyntheticPatientRepository(session), patients)
