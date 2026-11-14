import uuid
from datetime import datetime, timezone

import pytest

from app.conftest import FakeSyntheticPatientRepository, fake_synthetic_row
from app.constants.pagination import DEFAULT_PAGE_SIZE, SortOrder
from app.constants.patients import Gender
from app.constants.synthetic_patients import (
    DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD,
    SyntheticPatientSortField,
)
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.schemas import SyntheticPatientListQuery, SyntheticPatientRead
from app.synthetic_patients.seed import build_synthetic_values
from app.synthetic_patients.services import SyntheticPatientService

pytestmark = pytest.mark.anyio


def a_synthetic_patient(code: str = "P-1") -> SyntheticPatient:
    values = build_synthetic_values(fake_synthetic_row(patient_id=code), line=2)
    return SyntheticPatient(**values, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


async def test_list_returns_a_uniform_page_of_read_schemas() -> None:
    repository = FakeSyntheticPatientRepository([a_synthetic_patient("A"), a_synthetic_patient("B")])
    repository.total = 42

    page = await SyntheticPatientService(repository).list_synthetic_patients(
        SyntheticPatientListQuery(page=2, page_size=2)
    )

    assert (page.total, page.page, page.page_size) == (42, 2, 2)
    assert [item.code_synthetique for item in page.items] == ["A", "B"]
    assert all(isinstance(item, SyntheticPatientRead) for item in page.items)


async def test_list_turns_the_page_into_an_offset_and_a_limit() -> None:
    repository = FakeSyntheticPatientRepository()

    await SyntheticPatientService(repository).list_synthetic_patients(
        SyntheticPatientListQuery(page=3, page_size=10)
    )

    assert repository.last_criteria is not None
    assert (repository.last_criteria.offset, repository.last_criteria.limit) == (20, 10)


async def test_list_forwards_the_search_filters_and_sort() -> None:
    repository = FakeSyntheticPatientRepository()
    patient_id = uuid.uuid4()
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

    await SyntheticPatientService(repository).list_synthetic_patients(query)

    criteria = repository.last_criteria
    assert criteria is not None
    assert (criteria.search, criteria.patient_id, criteria.sexe) == ("SYN", patient_id, Gender.FEMALE)
    assert (criteria.jeu, criteria.phase) == ("actuel", "pre_greffe")
    assert (criteria.statut_parcours, criteria.organe) == ("En attente de greffe", "Rein")
    assert (criteria.sort_by, criteria.sort_order) == (SyntheticPatientSortField.AGE, SortOrder.DESC)


async def test_list_defaults() -> None:
    repository = FakeSyntheticPatientRepository()

    page = await SyntheticPatientService(repository).list_synthetic_patients(
        SyntheticPatientListQuery()
    )

    assert repository.last_criteria is not None
    assert repository.last_criteria.sort_by == DEFAULT_SYNTHETIC_PATIENT_SORT_FIELD
    assert repository.last_criteria.sort_order is SortOrder.ASC
    assert (page.page, page.page_size, page.items) == (1, DEFAULT_PAGE_SIZE, [])
