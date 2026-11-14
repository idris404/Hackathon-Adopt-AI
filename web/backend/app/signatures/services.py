import uuid

from app.constants.signatures import SIGN_QUEUE_SIZE
from app.patients.schemas import PatientRead
from app.patients.services import PatientService
from app.signatures.repository import SignatureRepository
from app.signatures.schemas import SignatureRead, SignQueueRead


class SignatureService:
    def __init__(self, repository: SignatureRepository, patients: PatientService) -> None:
        self._repository = repository
        self._patients = patients

    async def queue(self) -> SignQueueRead:
        patients = await self._repository.eligible(SIGN_QUEUE_SIZE)
        return SignQueueRead(
            items=[PatientRead.model_validate(patient) for patient in patients],
            remaining=await self._repository.count_eligible(),
        )

    async def sign(self, patient_uuid: uuid.UUID, user_id: uuid.UUID) -> SignatureRead:
        """`PatientNotFoundError` si le patient n'existe pas, `PatientAlreadySignedError` s'il
        est déjà signé."""
        patient = await self._patients.get_patient(patient_uuid)
        signature = await self._repository.add(patient.patient_id, user_id)
        return SignatureRead.model_validate(signature)
