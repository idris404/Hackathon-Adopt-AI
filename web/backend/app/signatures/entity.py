import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.patients import PATIENT_CODE_MAX_LENGTH
from app.constants.signatures import PATIENT_SIGNATURES_TABLE_NAME
from app.core.database import Base
from app.users.entity import User


class PatientSignature(Base):
    """Table `patient_signatures` : la validation d'un cas simple par un soignant.

    Une signature par patient (`patient_id` unique) ; elle ne s'annule pas. `signed_by` et
    `signed_at` assurent la traçabilité.

    `patient_id` (« HIS-00355 ») n'est pas une clé étrangère : `seed --reset` supprime et recrée
    `patients`, et une saisie de soignant doit survivre à ce reset. Le `patient_id` est stable
    d'un seed à l'autre, la signature retrouve donc son patient.
    """

    __tablename__ = PATIENT_SIGNATURES_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(PATIENT_CODE_MAX_LENGTH), unique=True)
    signed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey(f"{User.__tablename__}.id", ondelete="RESTRICT")
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
