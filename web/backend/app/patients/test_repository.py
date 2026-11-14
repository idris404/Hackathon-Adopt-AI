"""Requêtes SQL réelles (recherche, filtres, tri, pagination), sur SQLite en mémoire.

Le reste de la suite ne touche pas PostgreSQL ; SQLite suffit ici : les opérateurs utilisés
(`LIKE … ESCAPE`, `NULLS LAST`, `COUNT`, `OFFSET/LIMIT`) y sont les mêmes. `ON CONFLICT` du seed
est propre à PostgreSQL : il est vérifié en lançant le seed, pas ici.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.constants.pagination import SortOrder
from app.constants.patients import Gender, PatientSortField
from app.patients.entity import Patient
from app.patients.repository import PatientCriteria, PatientRepository

pytestmark = pytest.mark.anyio

DUPONT_JEAN = uuid.UUID(int=1)
DUPUIS_JEANNE = uuid.UUID(int=2)
DUPONT_MARIE = uuid.UUID(int=3)
PERCENT = uuid.UUID(int=4)
UNDERSCORE = uuid.UUID(int=5)
OTHER = uuid.UUID(int=6)


def patient(id: uuid.UUID, firstname: str, lastname: str, **overrides: object) -> Patient:
    values: dict[str, object] = {
        "patient_id": f"P-{id.int}",  # unique : un par id
        "gender": Gender.MALE,
        "birth": date(1980, 1, 1),
        "city": "Paris",
        "country": "France",
    }
    return Patient(id=id, firstname=firstname, lastname=lastname, **(values | overrides))


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Patient.__table__.create)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all(
            [
                patient(DUPONT_JEAN, "Jean", "Dupont", birth=date(1980, 5, 1), patient_id="SYN-0001"),
                patient(
                    DUPUIS_JEANNE, "Jeanne", "Dupuis", gender=Gender.FEMALE,
                    birth=date(1990, 7, 9), city="Lyon", patient_id="SYN-0002",
                ),  # fmt: skip
                patient(
                    DUPONT_MARIE, "Marie", "Dupont", gender=Gender.FEMALE, birth=None,
                    city="Bruxelles", country="Belgique",
                ),  # fmt: skip
                patient(PERCENT, "Pat", "Rate%Plus", birth=date(1970, 1, 1)),
                patient(UNDERSCORE, "Ugo", "Under_score", birth=date(1975, 1, 1)),
                patient(OTHER, "Zoé", "Zimmer", birth=date(2000, 12, 31), city="Genève", country="Suisse"),
            ]
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.fixture
def repository(session: AsyncSession) -> PatientRepository:
    return PatientRepository(session)


def criteria(**overrides: object) -> PatientCriteria:
    values: dict[str, object] = {
        "sort_by": PatientSortField.LASTNAME,
        "sort_order": SortOrder.ASC,
        "offset": 0,
        "limit": 50,
    }
    return PatientCriteria(**(values | overrides))


async def ids(repository: PatientRepository, **overrides: object) -> set[uuid.UUID]:
    patients, _ = await repository.find(criteria(**overrides))
    return {p.id for p in patients}


# --- recherche ---------------------------------------------------------------------------


async def test_search_matches_first_or_last_name_ignoring_case(repository) -> None:
    assert await ids(repository, search="DUPONT") == {DUPONT_JEAN, DUPONT_MARIE}
    assert await ids(repository, search="marie") == {DUPONT_MARIE}


async def test_search_matches_part_of_a_name(repository) -> None:
    assert await ids(repository, search="jean") == {DUPONT_JEAN, DUPUIS_JEANNE}


async def test_every_word_of_the_search_must_match(repository) -> None:
    # « jean » est aussi dans « Jeanne », mais « dupont » écarte Dupuis.
    assert await ids(repository, search="jean dupont") == {DUPONT_JEAN}
    # L'ordre des mots n'importe pas, prénom et nom se combinent.
    assert await ids(repository, search="dupont jean") == {DUPONT_JEAN}


async def test_search_matches_the_patient_id(repository) -> None:
    assert await ids(repository, search="syn-0001") == {DUPONT_JEAN}
    assert await ids(repository, search="SYN") == {DUPONT_JEAN, DUPUIS_JEANNE}
    # Les mots se combinent avec le prénom : « jean » est dans Jean et Jeanne, « 0002 » dans Jeanne.
    assert await ids(repository, search="jean 0002") == {DUPUIS_JEANNE}


async def test_search_does_not_look_at_city_or_country(repository) -> None:
    assert await ids(repository, search="Paris") == set()
    assert await ids(repository, search="France") == set()


async def test_like_wildcards_in_the_search_are_plain_text(repository) -> None:
    # Sans échappement, « % » correspondrait à tout et « _ » à n'importe quel caractère.
    assert await ids(repository, search="%") == {PERCENT}
    assert await ids(repository, search="_") == {UNDERSCORE}


async def test_a_blank_search_applies_no_filter(repository) -> None:
    assert len(await ids(repository, search="")) == 6
    assert len(await ids(repository, search="   ")) == 6


# --- filtres -----------------------------------------------------------------------------


async def test_gender_filter(repository) -> None:
    assert await ids(repository, gender=Gender.FEMALE) == {DUPUIS_JEANNE, DUPONT_MARIE}


async def test_city_and_country_filters_are_exact_and_case_insensitive(repository) -> None:
    assert await ids(repository, city="lyon") == {DUPUIS_JEANNE}
    assert await ids(repository, country="BELGIQUE") == {DUPONT_MARIE}
    assert await ids(repository, city="Lyo") == set()  # pas une recherche partielle


async def test_birth_range_is_inclusive_and_excludes_unknown_birth(repository) -> None:
    result = await ids(repository, birth_from=date(1980, 5, 1), birth_to=date(1990, 7, 9))

    assert result == {DUPONT_JEAN, DUPUIS_JEANNE}  # bornes incluses ; Marie (sans naissance) exclue


async def test_filters_combine(repository) -> None:
    result = await ids(repository, search="dupont", gender=Gender.FEMALE, country="Belgique")

    assert result == {DUPONT_MARIE}


async def test_no_match_returns_nothing_and_a_zero_total(repository) -> None:
    assert await repository.find(criteria(search="introuvable")) == ([], 0)


# --- tri ---------------------------------------------------------------------------------


async def test_sort_by_lastname_both_directions(repository) -> None:
    ascending, _ = await repository.find(criteria(search="dup", sort_order=SortOrder.ASC))
    descending, _ = await repository.find(criteria(search="dup", sort_order=SortOrder.DESC))

    assert [p.lastname for p in ascending] == ["Dupont", "Dupont", "Dupuis"]
    assert [p.lastname for p in descending] == ["Dupuis", "Dupont", "Dupont"]


@pytest.mark.parametrize("order", [SortOrder.ASC, SortOrder.DESC])
async def test_unknown_birth_is_always_last(repository, order: SortOrder) -> None:
    patients, _ = await repository.find(criteria(sort_by=PatientSortField.BIRTH, sort_order=order))

    assert patients[-1].id == DUPONT_MARIE
    births = [p.birth for p in patients[:-1]]
    assert births == sorted(births, reverse=order is SortOrder.DESC)


async def test_sort_by_patient_id(repository) -> None:
    found, _ = await repository.find(
        criteria(search="syn", sort_by=PatientSortField.PATIENT_ID, sort_order=SortOrder.DESC)
    )

    assert [p.patient_id for p in found] == ["SYN-0002", "SYN-0001"]


# --- pagination --------------------------------------------------------------------------


async def test_total_counts_every_match_not_just_the_page(repository) -> None:
    patients, total = await repository.find(criteria(limit=2))

    assert len(patients) == 2
    assert total == 6


async def test_pages_do_not_overlap_even_when_the_sort_key_ties(repository) -> None:
    # Deux « Dupont » : sans critère de départage, la frontière entre pages serait instable.
    seen: list[uuid.UUID] = []
    for offset in range(0, 6, 2):
        patients, _ = await repository.find(criteria(offset=offset, limit=2))
        seen.extend(p.id for p in patients)

    assert len(seen) == 6
    assert len(set(seen)) == 6


async def test_a_page_past_the_end_is_empty_but_keeps_the_total(repository) -> None:
    assert await repository.find(criteria(offset=60, limit=10)) == ([], 6)


# --- lecture d'un patient ----------------------------------------------------------------


async def test_get_by_id(repository) -> None:
    found = await repository.get_by_id(DUPONT_JEAN)

    assert found is not None
    assert found.firstname == "Jean"


async def test_get_by_id_of_an_unknown_patient_returns_none(repository) -> None:
    assert await repository.get_by_id(uuid.uuid4()) is None


# --- patient_id existants (utilisés par le seed des patients synthétiques) --------------


async def test_existing_patient_ids_keeps_only_the_ids_of_patients(repository) -> None:
    assert await repository.existing_patient_ids({"SYN-0001", "SYN-0002", "inconnu"}) == {
        "SYN-0001",
        "SYN-0002",
    }


async def test_existing_patient_ids_of_nothing_is_nothing(repository) -> None:
    assert await repository.existing_patient_ids(set()) == set()


async def test_the_patient_id_is_unique(session: AsyncSession) -> None:
    session.add(patient(uuid.uuid4(), "Copie", "Conforme", patient_id="SYN-0001"))

    with pytest.raises(IntegrityError):
        await session.commit()
