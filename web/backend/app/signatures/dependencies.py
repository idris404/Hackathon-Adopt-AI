from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.patients.dependencies import get_patient_service
from app.patients.services import PatientService
from app.signatures.repository import SignatureRepository
from app.signatures.services import SignatureService


def get_signature_service(
    session: AsyncSession = Depends(get_async_session),
    patients: PatientService = Depends(get_patient_service),
) -> SignatureService:
    return SignatureService(SignatureRepository(session), patients)
