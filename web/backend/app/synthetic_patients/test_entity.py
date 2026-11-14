"""La relation patient → patients synthétiques, sur SQLite en mémoire.

La liaison se fait par `patients_synthetiques.patient_id` → `patients.patient_id` (identifiant
fonctionnel unique), pas par `patients.id`. Un patient peut avoir plusieurs patients synthétiques.
Les clés étrangères sont actives (`PRAGMA foreign_keys`) : SQLite les ignore par défaut,
PostgreSQL non.
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.conftest import fake_synthetic_row, make_patient
from app.core.database import Base
from app.patients.entity import Patient
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.seed import build_synthetic_values

pytestmark = pytest.mark.anyio


def synthetic_of(patient_id: str, key: str | None = None) -> SyntheticPatient:
    """Un patient synthétique du patient de ce `patient_id`. `key` rend son `id` distinct."""
    values = build_synthetic_values(fake_synthetic_row(patient_id=key or patient_id), line=2)
    values["patient_id"] = patient_id  # plusieurs patients synthétiques pour un même patient
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


async def count_of(session: AsyncSession, patient_id: str) -> int:
    rows = await session.scalars(
        select(SyntheticPatient.id).where(SyntheticPatient.patient_id == patient_id)
    )
    return len(rows.all())


async def test_a_patient_can_have_several_synthetic_patients(session: AsyncSession) -> None:
    patient, other = make_patient(), make_patient()
    session.add_all(
        [patient, other, synthetic_of(patient.patient_id, "A"), synthetic_of(patient.patient_id, "B"),
         synthetic_of(other.patient_id, "C")]
    )  # fmt: skip
    await session.commit()

    assert await count_of(session, patient.patient_id) == 2
    assert await count_of(session, other.patient_id) == 1


async def test_a_synthetic_patient_knows_its_patient(session: AsyncSession) -> None:
    patient = make_patient()
    session.add_all([patient, synthetic_of(patient.patient_id)])
    await session.commit()

    synthetic = await session.scalar(
        select(SyntheticPatient).options(selectinload(SyntheticPatient.patient))
    )

    assert synthetic is not None
    assert synthetic.patient.id == patient.id


async def test_a_synthetic_patient_needs_an_existing_patient_id(session: AsyncSession) -> None:
    session.add(synthetic_of("inconnu"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_the_link_is_the_patient_id_not_the_id(session: AsyncSession) -> None:
    # Garde-fou : pointer vers l'UUID `id` du patient ne doit pas être accepté.
    patient = make_patient()
    session.add_all([patient, synthetic_of(str(patient.id))])

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_the_patient_id_of_a_patient_is_unique(session: AsyncSession) -> None:
    session.add_all([make_patient(patient_id="SYN-1"), make_patient(patient_id="SYN-1")])

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_a_patient_deletes_its_synthetic_patients_only(
    session: AsyncSession,
) -> None:
    deleted, kept = make_patient(), make_patient()
    session.add_all(
        [deleted, kept, synthetic_of(deleted.patient_id, "A"), synthetic_of(deleted.patient_id, "B"),
         synthetic_of(kept.patient_id, "C")]
    )  # fmt: skip
    await session.commit()

    await session.execute(delete(Patient).where(Patient.id == deleted.id))
    await session.commit()

    assert await count_of(session, deleted.patient_id) == 0
    assert await count_of(session, kept.patient_id) == 1


async def test_the_relation_is_not_loaded_implicitly(session: AsyncSession) -> None:
    # En asynchrone, un chargement implicite échouerait de façon obscure : on exige un chargement
    # explicite, et l'erreur dit clairement lequel.
    patient = make_patient()
    session.add_all([patient, synthetic_of(patient.patient_id)])
    await session.commit()
    loaded = await session.scalar(select(SyntheticPatient))

    assert loaded is not None
    with pytest.raises(InvalidRequestError):
        loaded.patient
