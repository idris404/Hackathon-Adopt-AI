import uuid
from datetime import datetime, timezone

import pytest

from app.conftest import (
    FakePatientRepository,
    FakeSyntheticPatientRepository,
    fake_synthetic_row,
    make_patient,
)
from app.constants.pagination import DEFAULT_PAGE_SIZE, SortOrder
from app.constants.patients import Gender
from app.constants.synthetic_patients import (
    DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD,
    SyntheticPatientSortField,
)
from app.patients.entity import Patient
from app.patients.exceptions import PatientNotFoundError
from app.patients.services import PatientService
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.schemas import (
    SyntheticPatientListQuery,
    SyntheticPatientPageQuery,
    SyntheticPatientRead,
)
from app.synthetic_patients.seed import build_synthetic_values
from app.synthetic_patients.services import SyntheticPatientService

pytestmark = pytest.mark.anyio


def a_patient() -> Patient:
    return make_patient()


def service_for(
    repository: FakeSyntheticPatientRepository, *patients: Patient
) -> SyntheticPatientService:
    """Le service, avec les patients donnés comme seuls patients existants."""
    return SyntheticPatientService(repository, PatientService(FakePatientRepository(list(patients))))


def a_synthetic_patient(code: str = "P-1") -> SyntheticPatient:
    values = build_synthetic_values(fake_synthetic_row(patient_id=code), line=2)
    return SyntheticPatient(**values, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


async def test_list_returns_a_uniform_page_of_read_schemas() -> None:
    repository = FakeSyntheticPatientRepository([a_synthetic_patient("A"), a_synthetic_patient("B")])
    repository.total = 42

    page = await service_for(repository).list_synthetic_patients(
        SyntheticPatientListQuery(page=2, page_size=2)
    )

    assert (page.total, page.page, page.page_size) == (42, 2, 2)
    assert [item.patient_id for item in page.items] == ["A", "B"]
    assert all(isinstance(item, SyntheticPatientRead) for item in page.items)


async def test_list_turns_the_page_into_an_offset_and_a_limit() -> None:
    repository = FakeSyntheticPatientRepository()

    await service_for(repository).list_synthetic_patients(
        SyntheticPatientListQuery(page=3, page_size=10)
    )

    assert repository.last_criteria is not None
    assert (repository.last_criteria.offset, repository.last_criteria.limit) == (20, 10)


async def test_list_forwards_the_search_filters_and_sort() -> None:
    repository = FakeSyntheticPatientRepository()
    patient_id = "SYN-0001"
    query = SyntheticPatientListQuery(
        search="SYN",
        patient_id=patient_id,
        sexe=Gender.FEMALE,
        jeu="actuel",
        phase="pre_greffe",
        statut_parcours="En attente de greffe",
        organe="Rein",
        sort_by=SyntheticPatientSortField.AGE,
        sort_order=SortOrder.DESC,
    )

    await service_for(repository).list_synthetic_patients(query)

    criteria = repository.last_criteria
    assert criteria is not None
    assert (criteria.search, criteria.patient_id, criteria.sexe) == ("SYN", patient_id, Gender.FEMALE)
    assert (criteria.jeu, criteria.phase) == ("actuel", "pre_greffe")
    assert (criteria.statut_parcours, criteria.organe) == ("En attente de greffe", "Rein")
    assert (criteria.sort_by, criteria.sort_order) == (SyntheticPatientSortField.AGE, SortOrder.DESC)


async def test_list_defaults() -> None:
    repository = FakeSyntheticPatientRepository()

    page = await service_for(repository).list_synthetic_patients(
        SyntheticPatientListQuery()
    )

    assert repository.last_criteria is not None
    assert repository.last_criteria.sort_by == DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD
    assert repository.last_criteria.sort_order is SortOrder.ASC
    assert (page.page, page.page_size, page.items) == (1, DEFAULT_PAGE_SIZE, [])


# --- les patients synthétiques d'un patient ----------------------------------------------


async def test_list_for_patient_links_by_the_patient_id_not_the_uuid() -> None:
    patient = a_patient()
    repository = FakeSyntheticPatientRepository([a_synthetic_patient("A"), a_synthetic_patient("B")])

    page = await service_for(repository, patient).list_for_patient(
        patient.id, SyntheticPatientPageQuery(page=2, page_size=5)
    )

    criteria = repository.last_criteria
    assert criteria is not None
    # L'URL désigne le patient par son `id` (UUID), la liaison se fait par son `patient_id`.
    assert criteria.patient_id == patient.patient_id
    assert criteria.patient_id != str(patient.id)
    assert (criteria.offset, criteria.limit) == (5, 5)
    assert (page.page, page.page_size, page.total) == (2, 5, 2)
    assert [item.patient_id for item in page.items] == ["A", "B"]


async def test_list_for_patient_keeps_the_sort() -> None:
    patient = a_patient()
    repository = FakeSyntheticPatientRepository()
    query = SyntheticPatientPageQuery(sort_by=SyntheticPatientSortField.AGE, sort_order=SortOrder.DESC)

    await service_for(repository, patient).list_for_patient(patient.id, query)

    assert repository.last_criteria is not None
    assert (repository.last_criteria.sort_by, repository.last_criteria.sort_order) == (
        SyntheticPatientSortField.AGE,
        SortOrder.DESC,
    )


async def test_a_patient_without_synthetic_patients_gets_an_empty_page() -> None:
    patient = a_patient()

    page = await service_for(FakeSyntheticPatientRepository(), patient).list_for_patient(
        patient.id, SyntheticPatientPageQuery()
    )

    assert (page.items, page.total) == ([], 0)


async def test_an_unknown_patient_is_an_error_not_an_empty_page() -> None:
    repository = FakeSyntheticPatientRepository([a_synthetic_patient()])

    with pytest.raises(PatientNotFoundError):
        await service_for(repository, a_patient()).list_for_patient(
            uuid.uuid4(), SyntheticPatientPageQuery()
        )

    assert repository.last_criteria is None  # la liste n'a même pas été interrogée
