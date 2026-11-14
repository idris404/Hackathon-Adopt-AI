import uuid
from datetime import date, datetime
from typing import Annotated

from sqlalchemy import Date, DateTime, Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.patients import (
    CITY_MAX_LENGTH,
    COUNTRY_MAX_LENGTH,
    FIRSTNAME_MAX_LENGTH,
    LASTNAME_MAX_LENGTH,
    PATIENT_CODE_MAX_LENGTH,
    PATIENTS_TABLE_NAME,
    Gender,
)
from app.core.database import Base

# Stocke la valeur ("M" / "F") et non le nom du membre ; VARCHAR, pas de type enum natif
# (pas d'outil de migration pour faire évoluer un type PostgreSQL).
GenderColumn = Annotated[
    Gender,
    mapped_column(
        Enum(Gender, native_enum=False, values_callable=lambda members: [m.value for m in members])
    ),
]


class Patient(Base):
    """Table `patients` : identité seulement (aucune donnée clinique).

    `patient_id` est l'identifiant fonctionnel unique du patient (« SYN-0001 », la colonne
    `patient_id` du CSV) ; `id` est sa clé primaire technique. Un patient peut avoir plusieurs
    patients synthétiques : ils pointent vers lui par leur `patient_id` (contexte
    `synthetic_patients`), pas par son `id`.
    """

    __tablename__ = PATIENTS_TABLE_NAME

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(PATIENT_CODE_MAX_LENGTH), unique=True)
    firstname: Mapped[str] = mapped_column(String(FIRSTNAME_MAX_LENGTH))
    lastname: Mapped[str] = mapped_column(String(LASTNAME_MAX_LENGTH))
    # Nullable : la source contient des patients sans date de naissance renseignée.
    birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[GenderColumn]
    city: Mapped[str] = mapped_column(String(CITY_MAX_LENGTH))
    country: Mapped[str] = mapped_column(String(COUNTRY_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
