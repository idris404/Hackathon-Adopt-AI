import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.constants.pagination import LIKE_ESCAPE_CHARACTER, SortOrder
from app.constants.patients import Gender, PatientSortField
from app.patients.entity import Patient

# Tri : liste blanche. Le client envoie un `PatientSortField`, jamais un nom de colonne brut.
SORT_COLUMNS: dict[PatientSortField, InstrumentedAttribute] = {
    PatientSortField.FIRSTNAME: Patient.firstname,
    PatientSortField.LASTNAME: Patient.lastname,
    PatientSortField.BIRTH: Patient.birth,
    PatientSortField.GENDER: Patient.gender,
    PatientSortField.CITY: Patient.city,
    PatientSortField.COUNTRY: Patient.country,
    PatientSortField.CREATED_AT: Patient.created_at,
}

SEARCH_COLUMNS = (Patient.firstname, Patient.lastname)


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


def _escape_like(value: str) -> str:
    """Neutralise `%` et `_` : la saisie de l'utilisateur est du texte, pas un motif."""
    escape = LIKE_ESCAPE_CHARACTER
    return value.replace(escape, escape * 2).replace("%", f"{escape}%").replace("_", f"{escape}_")


def _contains(column: InstrumentedAttribute, term: str) -> ColumnElement[bool]:
    return column.ilike(f"%{_escape_like(term)}%", escape=LIKE_ESCAPE_CHARACTER)


def _equals_ignoring_case(column: InstrumentedAttribute, value: str) -> ColumnElement[bool]:
    return column.ilike(_escape_like(value), escape=LIKE_ESCAPE_CHARACTER)


def _conditions(criteria: PatientCriteria) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if criteria.search:
        # Un mot = une condition (ET) ; chaque mot peut se trouver dans le prénom OU le nom.
        for term in criteria.search.split():
            conditions.append(or_(*(_contains(column, term) for column in SEARCH_COLUMNS)))
    if criteria.gender:
        conditions.append(Patient.gender == criteria.gender)
    if criteria.city:
        conditions.append(_equals_ignoring_case(Patient.city, criteria.city))
    if criteria.country:
        conditions.append(_equals_ignoring_case(Patient.country, criteria.country))
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
            .order_by(direction.nulls_last(), Patient.id)  # `id` : ordre stable entre deux pages
            .offset(criteria.offset)
            .limit(criteria.limit)
        )
        return list(rows), total or 0

    async def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        return await self._session.get(Patient, patient_id)

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        """Insère les patients dont l'id est absent ; renvoie le nombre réellement insérés."""
        result = await self._session.execute(
            insert(Patient).values(list(values)).on_conflict_do_nothing(index_elements=["id"])
        )
        return result.rowcount
