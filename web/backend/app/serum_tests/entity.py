import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.patients import PATIENT_CODE_MAX_LENGTH, PATIENTS_TABLE_NAME
from app.constants.serum_tests import PROFILE_MAX_LENGTH, SERUM_TESTS_TABLE_NAME
from app.core.database import Base
from app.patients.entity import Patient


class SerumTest(Base):
    """Table `serum_tests` : un prélèvement sérique du CSV `serum_test_history.csv`.

    Lié au patient par `patient_id` (ex. « HIS-00355 »), clé étrangère vers
    `patients.patient_id`, pas vers `patients.id`. Un patient a un test par année :
    (`patient_id`, `test_date`) est unique. Les colonnes reprennent le CSV en minuscules
    (`B12` → `b12`). `*_output` vaut 1 si la valeur atteint 500, 0 sinon.
    """

    __tablename__ = SERUM_TESTS_TABLE_NAME
    __table_args__ = (UniqueConstraint("patient_id", "test_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(
        String(PATIENT_CODE_MAX_LENGTH),
        ForeignKey(f"{PATIENTS_TABLE_NAME}.patient_id", ondelete="CASCADE"),
        index=True,
    )
    patient: Mapped[Patient] = relationship(back_populates="serum_tests", lazy="raise")
    graft_date: Mapped[date] = mapped_column(Date)
    test_date: Mapped[date] = mapped_column(Date)
    b12: Mapped[int] = mapped_column(Integer)
    b12_output: Mapped[int] = mapped_column(Integer)
    b13: Mapped[int] = mapped_column(Integer)
    b13_output: Mapped[int] = mapped_column(Integer)
    dr53: Mapped[int] = mapped_column(Integer)
    dr53_output: Mapped[int] = mapped_column(Integer)
    dr51: Mapped[int] = mapped_column(Integer)
    dr51_output: Mapped[int] = mapped_column(Integer)
    dq10: Mapped[int] = mapped_column(Integer)
    dq10_output: Mapped[int] = mapped_column(Integer)
    profile: Mapped[str] = mapped_column(String(PROFILE_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
