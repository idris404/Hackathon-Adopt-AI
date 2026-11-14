import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.patients.schemas import PatientRead


class SignQueueRead(BaseModel):
    """La file « À signer » : les premiers cas simples et le nombre total de cas restants."""

    items: list[PatientRead]
    remaining: int


class SignatureCreate(BaseModel):
    """Entrée : l'UUID du patient à signer (pas son `patient_id`)."""

    model_config = ConfigDict(extra="forbid")

    patient_id: uuid.UUID


class SignatureRead(BaseModel):
    """Une signature. `patient_id` est l'identifiant fonctionnel (« HIS-00355 »)."""

    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    signed_by: uuid.UUID
    signed_at: datetime
