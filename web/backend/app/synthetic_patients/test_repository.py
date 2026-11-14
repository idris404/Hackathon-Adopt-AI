"""Requêtes SQL réelles (recherche, filtres, tri, pagination), sur SQLite en mémoire.

Les valeurs de test restent en ASCII : `lower()` de SQLite ne gère pas les accents, PostgreSQL oui.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.conftest import fake_synthetic_row, make_patient
from app.constants.pagination import SortOrder
from app.constants.patients import Gender
from app.constants.synthetic_patients import SyntheticPatientSortField
from app.core.database import Base
from app.patients.entity import Patient
from app.synthetic_patients.entity import SyntheticPatient
from app.synthetic_patients.repository import (
    SyntheticPatientCriteria,
    SyntheticPatientRepository,
)
from app.synthetic_patients.seed import build_synthetic_values

pytestmark = pytest.mark.anyio

PATIENT_IDS = ("SYN-0001", "SYN-0002", "HIS-0001", "A%B", "A_B")


def synthetic(patient_id: str, key: str, **overrides: str) -> SyntheticPatient:
    """Un patient synthétique fictif du patient `patient_id`. `key` rend son `id` distinct, ce qui
    permet d'en créer plusieurs pour un même patient. `overrides` : colonnes telles que dans le CSV."""
    values = build_synthetic_values(fake_synthetic_row(patient_id=key, **overrides), line=2)
    values["patient_id"] = patient_id
    return SyntheticPatient(**values)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all, tables=[Patient.__table__, SyntheticPatient.__table__]
        )
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all([make_patient(patient_id=patient_id) for patient_id in PATIENT_IDS])
        session.add_all(
            [
                # SYN-0001 a DEUX patients synthétiques : un patient peut en avoir plusieurs.
                synthetic("SYN-0001", "a", jeu="actuel", phase="pre_greffe", organe="Rein",
                          statut_parcours="Attente", sexe="M", age="30"),
                synthetic("SYN-0001", "b", jeu="historique", phase="post_greffe", organe="Rein",
                          statut_parcours="Greffe", sexe="F", age="50"),
                synthetic("SYN-0002", "c", jeu="historique", phase="post_greffe",
                          organe="Rein-Pancreas", statut_parcours="Greffe", sexe="M", age=""),
                synthetic("HIS-0001", "d", jeu="historique", phase="post_greffe", organe="Rein",
                          statut_parcours="Greffe", sexe="F", age="40"),
                synthetic("A%B", "e"), synthetic("A_B", "f"),
            ]
        )  # fmt: skip
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def repository(session: AsyncSession) -> SyntheticPatientRepository:
    return SyntheticPatientRepository(session)


def criteria(**overrides: object) -> SyntheticPatientCriteria:
    values: dict[str, object] = {
        "sort_by": SyntheticPatientSortField.PATIENT_ID,
        "sort_order": SortOrder.ASC,
        "offset": 0,
        "limit": 50,
    }
    return SyntheticPatientCriteria(**(values | overrides))


async def patient_ids(repository: SyntheticPatientRepository, **overrides: object) -> list[str]:
    found, _ = await repository.find(criteria(**overrides))
    return [item.patient_id for item in found]


# --- recherche ---------------------------------------------------------------------------


async def test_search_looks_into_the_patient_id_ignoring_case(repository) -> None:
    assert await patient_ids(repository, search="syn-000") == ["SYN-0001", "SYN-0001", "SYN-0002"]
    assert await patient_ids(repository, search="HIS") == ["HIS-0001"]


async def test_like_wildcards_in_the_search_are_plain_text(repository) -> None:
    assert await patient_ids(repository, search="%") == ["A%B"]
    assert await patient_ids(repository, search="_") == ["A_B"]


async def test_a_blank_search_applies_no_filter(repository) -> None:
    assert len(await patient_ids(repository, search="")) == 6


# --- filtres -----------------------------------------------------------------------------


async def test_all_the_synthetic_patients_of_one_patient(repository) -> None:
    # Les deux patients synthétiques de SYN-0001, et seulement eux.
    assert await patient_ids(repository, patient_id="SYN-0001") == ["SYN-0001", "SYN-0001"]
    assert await patient_ids(repository, patient_id="syn-0001") == ["SYN-0001", "SYN-0001"]


async def test_the_patient_id_filter_is_exact_not_partial(repository) -> None:
    assert await patient_ids(repository, patient_id="SYN") == []
    assert await patient_ids(repository, patient_id="inconnu") == []


async def test_sexe_filter(repository) -> None:
    assert await patient_ids(repository, sexe=Gender.FEMALE) == ["HIS-0001", "SYN-0001"]


async def test_category_filters_are_exact_and_case_insensitive(repository) -> None:
    assert await patient_ids(repository, jeu="ACTUEL") == ["SYN-0001"]
    assert await patient_ids(repository, phase="pre_greffe") == ["SYN-0001"]
    # « Rein » n'est pas une recherche partielle : « Rein-Pancreas » n'en fait pas partie.
    assert await patient_ids(repository, organe="rein") == ["HIS-0001", "SYN-0001", "SYN-0001"]


async def test_filters_combine(repository) -> None:
    assert await patient_ids(repository, patient_id="SYN-0001", sexe=Gender.FEMALE) == ["SYN-0001"]
    assert await patient_ids(repository, statut_parcours="greffe", sexe=Gender.FEMALE) == [
        "HIS-0001",
        "SYN-0001",
    ]


async def test_no_match_returns_nothing_and_a_zero_total(repository) -> None:
    assert await repository.find(criteria(search="introuvable")) == ([], 0)


# --- tri ---------------------------------------------------------------------------------


async def test_sort_by_patient_id_both_directions(repository) -> None:
    ascending = await patient_ids(repository, search="-0", sort_order=SortOrder.ASC)
    descending = await patient_ids(repository, search="-0", sort_order=SortOrder.DESC)

    assert ascending == ["HIS-0001", "SYN-0001", "SYN-0001", "SYN-0002"]
    assert descending == ascending[::-1]


@pytest.mark.parametrize("order", [SortOrder.ASC, SortOrder.DESC])
async def test_an_unknown_age_is_always_last(repository, order: SortOrder) -> None:
    found, _ = await repository.find(
        criteria(search="-0", sort_by=SyntheticPatientSortField.AGE, sort_order=order)
    )

    assert found[-1].patient_id == "SYN-0002"  # le seul sans âge
    ages = [item.age for item in found[:-1]]
    assert ages == sorted(ages, reverse=order is SortOrder.DESC)


# --- pagination --------------------------------------------------------------------------


async def test_total_counts_every_match_not_just_the_page(repository) -> None:
    found, total = await repository.find(criteria(limit=2))

    assert len(found) == 2
    assert total == 6


async def test_pages_do_not_overlap_even_when_the_sort_key_ties(repository) -> None:
    # Tri sur `phase` : cinq patients synthétiques ont la même valeur, l'ordre doit rester stable.
    seen: list[uuid.UUID] = []
    for offset in range(0, 6, 2):
        found, _ = await repository.find(
            criteria(sort_by=SyntheticPatientSortField.PHASE, offset=offset, limit=2)
        )
        seen.extend(item.id for item in found)

    assert len(seen) == len(set(seen)) == 6


async def test_a_page_past_the_end_is_empty_but_keeps_the_total(repository) -> None:
    assert await repository.find(criteria(offset=60, limit=10)) == ([], 6)
