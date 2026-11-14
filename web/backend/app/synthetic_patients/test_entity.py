"""La relation patient → patients synthétiques (un patient en a plusieurs), sur SQLite en mémoire.

Les clés étrangères sont actives (`PRAGMA foreign_keys`) : SQLite les ignore par défaut,
PostgreSQL non.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.conftest import fake_synthetic_row
from app.constants.patients import Gender
from app.core.database import Base
from app.patients.entity import Patient
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.seed import build_synthetic_values

pytestmark = pytest.mark.anyio


def a_patient() -> Patient:
    return Patient(
        id=uuid.uuid4(),
        firstname="Ada",
        lastname="Test",
        gender=Gender.FEMALE,
        city="Lille",
        country="France",
    )


def synthetic_of(patient: Patient, code: str) -> SyntheticPatient:
    values = build_synthetic_values(fake_synthetic_row(patient_id=code), line=2)
    values["patient_id"] = patient.id  # plusieurs codes pour un même patient
    return SyntheticPatient(**values)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")

    @event.listens_for(engine.sync_engine, "connect")
    def enforce_foreign_keys(connection, _) -> None:  # noqa: ANN001
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all, tables=[Patient.__table__, SyntheticPatient.__table__]
        )
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


async def codes_of(session: AsyncSession, patient: Patient) -> set[str]:
    rows = await session.scalars(
        select(SyntheticPatient.code_synthetique).where(SyntheticPatient.patient_id == patient.id)
    )
    return set(rows)


async def test_a_patient_can_have_several_synthetic_patients(session: AsyncSession) -> None:
    patient, other = a_patient(), a_patient()
    session.add_all(
        [patient, other, synthetic_of(patient, "SYN-A"), synthetic_of(patient, "SYN-B"),
         synthetic_of(other, "SYN-C")]
    )  # fmt: skip
    await session.commit()

    assert await codes_of(session, patient) == {"SYN-A", "SYN-B"}
    assert await codes_of(session, other) == {"SYN-C"}


async def test_a_synthetic_patient_knows_its_patient(session: AsyncSession) -> None:
    patient = a_patient()
    session.add_all([patient, synthetic_of(patient, "SYN-A")])
    await session.commit()

    synthetic = await session.scalar(
        select(SyntheticPatient).options(selectinload(SyntheticPatient.patient))
    )

    assert synthetic is not None
    assert synthetic.patient.id == patient.id


async def test_a_synthetic_patient_needs_an_existing_patient(session: AsyncSession) -> None:
    orphan = synthetic_of(a_patient(), "SYN-A")  # son patient n'est pas enregistré

    session.add(orphan)

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_the_synthetic_code_is_unique(session: AsyncSession) -> None:
    patient = a_patient()
    session.add_all([patient, synthetic_of(patient, "SYN-A")])
    await session.commit()

    duplicate = synthetic_of(patient, "SYN-A")
    duplicate.id = uuid.uuid4()
    session.add(duplicate)

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_a_patient_deletes_its_synthetic_patients_only(
    session: AsyncSession,
) -> None:
    deleted, kept = a_patient(), a_patient()
    session.add_all(
        [deleted, kept, synthetic_of(deleted, "SYN-A"), synthetic_of(deleted, "SYN-B"),
         synthetic_of(kept, "SYN-C")]
    )  # fmt: skip
    await session.commit()

    await session.execute(delete(Patient).where(Patient.id == deleted.id))
    await session.commit()

    remaining = (await session.scalars(select(SyntheticPatient.code_synthetique))).all()
    assert remaining == ["SYN-C"]


async def test_the_relation_is_not_loaded_implicitly(session: AsyncSession) -> None:
    # En asynchrone, un chargement implicite échouerait de façon obscure : on exige un chargement
    # explicite, et l'erreur dit clairement lequel.
    patient = a_patient()
    session.add_all([patient, synthetic_of(patient, "SYN-A")])
    await session.commit()
    loaded = await session.scalar(select(SyntheticPatient))

    assert loaded is not None
    with pytest.raises(InvalidRequestError):
        loaded.patient
