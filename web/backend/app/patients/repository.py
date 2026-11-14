import uuid
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from app.constants.pagination import SortOrder
from app.constants.patients import Gender, PatientSortField
from app.core.search import contains, equals_ignoring_case
from app.patient_history.entity import PatientHistory  # noqa: F401 — enregistre la relation
from app.patients.entity import Patient
from app.serum_tests.entity import SerumTest  # noqa: F401 — enregistre la relation

# Tri : liste blanche. Le client envoie un `PatientSortField`, jamais un nom de colonne brut.
SORT_COLUMNS: dict[PatientSortField, InstrumentedAttribute] = {
    PatientSortField.PATIENT_ID: Patient.patient_id,
    PatientSortField.FIRSTNAME: Patient.firstname,
    PatientSortField.LASTNAME: Patient.lastname,
    PatientSortField.BIRTH: Patient.birth,
    PatientSortField.GENDER: Patient.gender,
    PatientSortField.CITY: Patient.city,
    PatientSortField.COUNTRY: Patient.country,
    PatientSortField.CREATED_AT: Patient.created_at,
}

SEARCH_COLUMNS = (Patient.patient_id, Patient.firstname, Patient.lastname)


@dataclass(frozen=True)
class PatientCriteria:
    """Ce que le repository sait interroger (pas un schéma Pydantic : il ignore le HTTP)."""

    sort_by: PatientSortField
    sort_order: SortOrder
    offset: int
    limit: int
    search: str | None = None
    gender: Gender | None = None
    city: str | None = None
    country: str | None = None
    birth_from: date | None = None
    birth_to: date | None = None


def _conditions(criteria: PatientCriteria) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if criteria.search:
        # Un mot = une condition (ET) ; chaque mot peut se trouver dans le patient_id, le prénom OU le nom.
        for term in criteria.search.split():
            conditions.append(or_(*(contains(column, term) for column in SEARCH_COLUMNS)))
    if criteria.gender:
        conditions.append(Patient.gender == criteria.gender)
    if criteria.city:
        conditions.append(equals_ignoring_case(Patient.city, criteria.city))
    if criteria.country:
        conditions.append(equals_ignoring_case(Patient.country, criteria.country))
    if criteria.birth_from:
        conditions.append(Patient.birth >= criteria.birth_from)
    if criteria.birth_to:
        conditions.append(Patient.birth <= criteria.birth_to)
    return conditions


class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, criteria: PatientCriteria) -> tuple[list[Patient], int]:
        """Une page de patients et le total des patients qui correspondent aux filtres."""
        conditions = _conditions(criteria)

        total = await self._session.scalar(
            select(func.count()).select_from(Patient).where(*conditions)
        )

        column = SORT_COLUMNS[criteria.sort_by]
        direction = column.desc() if criteria.sort_order is SortOrder.DESC else column.asc()
        rows = await self._session.scalars(
            select(Patient)
            .where(*conditions)
            .options(selectinload(Patient.serum_tests), selectinload(Patient.history))
            .order_by(direction.nulls_last(), Patient.id)  # `id` : ordre stable entre deux pages
            .offset(criteria.offset)
            .limit(criteria.limit)
        )
        return list(rows), total or 0

    async def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return await self._session.scalar(
            select(Patient)
            .where(Patient.id == patient_id)
            .options(selectinload(Patient.serum_tests), selectinload(Patient.history))
        )

    async def existing_patient_ids(self, patient_ids: Collection[str]) -> set[str]:
        """Parmi ces `patient_id`, ceux qui correspondent à un patient."""
        if not patient_ids:
            return set()
        rows = await self._session.scalars(
            select(Patient.patient_id).where(Patient.patient_id.in_(patient_ids))
        )
        return set(rows)

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        """Insère les patients absents ; renvoie le nombre réellement insérés.

        Un patient est « présent » si son `id` OU son `patient_id` existe déjà (les deux sont uniques).
        """
        result = await self._session.execute(
            insert(Patient).values(list(values)).on_conflict_do_nothing()
        )
        return result.rowcount
