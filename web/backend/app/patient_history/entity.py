import uuid
from datetime import date, datetime
from typing import Annotated

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.patient_history import (
    DETAIL_MAX_LENGTH,
    PATIENT_HISTORY_TABLE_NAME,
    TITLE_MAX_LENGTH,
    HistoryKind,
)
from app.constants.patients import PATIENT_CODE_MAX_LENGTH, PATIENTS_TABLE_NAME
from app.core.database import Base
from app.patients.entity import Patient

# Stocke la valeur ("graft", …) et non le nom du membre ; VARCHAR, pas de type enum natif.
HistoryKindColumn = Annotated[
    HistoryKind,
    mapped_column(
        Enum(
            HistoryKind,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        )
    ),
]


class PatientHistory(Base):
    """Table `patient_history` : un événement fictif du parcours d'un patient.

    Lié au patient par `patient_id` (ex. « HIS-00355 »), clé étrangère vers
    `patients.patient_id`, pas vers `patients.id`. Les textes sont des exemples
    de démonstration, pas des données cliniques.
    """

    __tablename__ = PATIENT_HISTORY_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(
        String(PATIENT_CODE_MAX_LENGTH),
        ForeignKey(f"{PATIENTS_TABLE_NAME}.patient_id", ondelete="CASCADE"),
        index=True,
    )
    patient: Mapped[Patient] = relationship(back_populates="history", lazy="raise")
    kind: Mapped[HistoryKindColumn]
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    detail: Mapped[str] = mapped_column(String(DETAIL_MAX_LENGTH))
    occurred_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
