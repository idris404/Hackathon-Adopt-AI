"""Requête de la file « À signer » et unicité de la signature, sur SQLite en mémoire."""

import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.conftest import make_history_event, make_patient, make_serum_test
from app.constants.signatures import SIGN_QUEUE_MAX_HISTORY_EVENTS
from app.patient_history.entity import PatientHistory
from app.patients.entity import Patient
from app.serum_tests.entity import SerumTest
from app.signatures.entity import PatientSignature
from app.signatures.exceptions import PatientAlreadySignedError
from app.signatures.repository import SignatureRepository
from app.users.entity import User

pytestmark = pytest.mark.anyio

SIGNER = uuid.UUID(int=99)


def with_profile(patient_id: str, profile: str, events: int = 0) -> list[object]:
    patient = make_patient(patient_id=patient_id)
    rows: list[object] = [patient, make_serum_test(patient, profile=profile)]
    rows += [
        make_history_event(patient, id=uuid.uuid4(), occurred_on=date(2015, 1, 1 + n))
        for n in range(events)
    ]
    return rows


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        for table in (User, Patient, SerumTest, PatientHistory, PatientSignature):
            await connection.run_sync(table.__table__.create)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add(User(id=SIGNER, email="signer@example.com", hashed_password="x"))
        session.add_all(
            [
                *with_profile("P-A-0", "A"),
                *with_profile("P-A-1", "A"),
                *with_profile("P-A-FEW", "A", events=SIGN_QUEUE_MAX_HISTORY_EVENTS),
                *with_profile("P-A-MANY", "A", events=SIGN_QUEUE_MAX_HISTORY_EVENTS + 1),
                *with_profile("P-B", "B"),
                *with_profile("P-C", "C"),
            ]
        )
        session.add(make_patient(patient_id="P-NO-TEST"))
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def repository(session: AsyncSession) -> SignatureRepository:
    return SignatureRepository(session)


async def codes(repository: SignatureRepository, limit: int = 10) -> list[str]:
    return [patient.patient_id for patient in await repository.eligible(limit)]


async def test_the_queue_keeps_constant_profiles_with_a_short_history(repository) -> None:
    # Le plus court historique d'abord, puis par `patient_id`.
    assert await codes(repository) == ["P-A-0", "P-A-1", "P-A-FEW"]
    assert await repository.count_eligible() == 3


async def test_the_queue_is_limited(repository) -> None:
    assert await codes(repository, limit=2) == ["P-A-0", "P-A-1"]
    assert await repository.count_eligible() == 3  # le total ignore la limite


async def test_a_signed_patient_leaves_the_queue(repository) -> None:
    signature = await repository.add("P-A-0", SIGNER)

    assert (signature.patient_id, signature.signed_by) == ("P-A-0", SIGNER)
    assert signature.signed_at is not None
    assert await codes(repository) == ["P-A-1", "P-A-FEW"]
    assert await repository.count_eligible() == 2


async def test_a_patient_is_signed_only_once(repository) -> None:
    await repository.add("P-A-0", SIGNER)

    with pytest.raises(PatientAlreadySignedError):
        await repository.add("P-A-0", SIGNER)
    assert await repository.count_eligible() == 2
