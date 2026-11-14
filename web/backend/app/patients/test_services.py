import uuid
from datetime import date, datetime, timezone

import pytest

from app.conftest import FakePatientRepository
from app.constants.pagination import DEFAULT_PAGE_SIZE, SortOrder
from app.constants.patients import DEFAULT_PATIENT_SORT_FIELD, Gender, PatientSortField
from app.patients.entity import Patient
from app.patients.exceptions import PatientNotFoundError
from app.patients.schemas import PatientListQuery, PatientRead
from app.patients.services import PatientService

pytestmark = pytest.mark.anyio


def a_patient() -> Patient:
    return Patient(
        id=uuid.uuid4(),
        firstname="Ada",
        lastname="Test",
        birth=date(1985, 3, 2),
        gender=Gender.FEMALE,
        city="Lille",
        country="France",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


async def test_list_returns_a_uniform_page_of_read_schemas() -> None:
    repository = FakePatientRepository([a_patient(), a_patient()])
    repository.total = 42

    page = await PatientService(repository).list_patients(PatientListQuery(page=2, page_size=2))

    assert (page.total, page.page, page.page_size) == (42, 2, 2)
    assert len(page.items) == 2
    assert all(isinstance(item, PatientRead) for item in page.items)


async def test_list_turns_the_page_into_an_offset_and_a_limit() -> None:
    repository = FakePatientRepository()

    await PatientService(repository).list_patients(PatientListQuery(page=3, page_size=10))

    assert repository.last_criteria is not None
    assert (repository.last_criteria.offset, repository.last_criteria.limit) == (20, 10)


async def test_list_forwards_the_search_filters_and_sort() -> None:
    repository = FakePatientRepository()
    query = PatientListQuery(
        search="dup",
        gender=Gender.FEMALE,
        city="Lyon",
        country="France",
        birth_from=date(1980, 1, 1),
        birth_to=date(1990, 1, 1),
        sort_by=PatientSortField.BIRTH,
        sort_order=SortOrder.DESC,
    )

    await PatientService(repository).list_patients(query)

    criteria = repository.last_criteria
    assert criteria is not None
    assert criteria.search == "dup"
    assert criteria.gender is Gender.FEMALE
    assert (criteria.city, criteria.country) == ("Lyon", "France")
    assert (criteria.birth_from, criteria.birth_to) == (date(1980, 1, 1), date(1990, 1, 1))
    assert (criteria.sort_by, criteria.sort_order) == (PatientSortField.BIRTH, SortOrder.DESC)


async def test_list_defaults() -> None:
    repository = FakePatientRepository()

    page = await PatientService(repository).list_patients(PatientListQuery())

    assert repository.last_criteria is not None
    assert repository.last_criteria.sort_by == DEFAULT_PATIENT_SORT_FIELD
    assert repository.last_criteria.sort_order is SortOrder.ASC
    assert (page.page, page.page_size, page.items) == (1, DEFAULT_PAGE_SIZE, [])


async def test_get_returns_the_patient() -> None:
    patient = a_patient()

    result = await PatientService(FakePatientRepository([patient])).get_patient(patient.id)

    assert result.id == patient.id
    assert result.lastname == patient.lastname


async def test_get_an_unknown_patient_raises() -> None:
    with pytest.raises(PatientNotFoundError):
        await PatientService(FakePatientRepository([a_patient()])).get_patient(uuid.uuid4())


async def test_the_service_tells_which_ids_are_patients() -> None:
    patient = a_patient()
    service = PatientService(FakePatientRepository([patient]))

    known = await service.existing_ids({patient.id, uuid.uuid4()})

    assert known == {patient.id}
