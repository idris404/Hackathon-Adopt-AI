from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.constants.pagination import SortOrder
from app.constants.patients import Gender
from app.constants.synthetic_patients import SyntheticPatientSortField
from app.core.search import contains, equals_ignoring_case
from app.synthetic_patients.entity import SyntheticPatient

# Tri : liste blanche. Le client envoie un `SyntheticPatientSortField`, jamais un nom de colonne.
SORT_COLUMNS: dict[SyntheticPatientSortField, InstrumentedAttribute] = {
    SyntheticPatientSortField.PATIENT_ID: SyntheticPatient.patient_id,
    SyntheticPatientSortField.DATE_REFERENCE: SyntheticPatient.date_reference,
    SyntheticPatientSortField.DATE_NAISSANCE: SyntheticPatient.date_naissance,
    SyntheticPatientSortField.AGE: SyntheticPatient.age,
    SyntheticPatientSortField.JEU: SyntheticPatient.jeu,
    SyntheticPatientSortField.PHASE: SyntheticPatient.phase,
    SyntheticPatientSortField.STATUT_PARCOURS: SyntheticPatient.statut_parcours,
    SyntheticPatientSortField.STATUT_DATE: SyntheticPatient.statut_date,
    SyntheticPatientSortField.ORGANE: SyntheticPatient.organe,
    SyntheticPatientSortField.CREATED_AT: SyntheticPatient.created_at,
}


@dataclass(frozen=True)
class SyntheticPatientCriteria:
    """Ce que le repository sait interroger (pas un schéma Pydantic : il ignore le HTTP)."""

    sort_by: SyntheticPatientSortField
    sort_order: SortOrder
    offset: int
    limit: int
    search: str | None = None
    patient_id: str | None = None
    sexe: Gender | None = None
    jeu: str | None = None
    phase: str | None = None
    statut_parcours: str | None = None
    organe: str | None = None


def _conditions(criteria: SyntheticPatientCriteria) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if criteria.search:
        conditions.append(contains(SyntheticPatient.patient_id, criteria.search))
    if criteria.patient_id:
        conditions.append(equals_ignoring_case(SyntheticPatient.patient_id, criteria.patient_id))
    if criteria.sexe:
        conditions.append(SyntheticPatient.sexe == criteria.sexe)
    for column, value in (
        (SyntheticPatient.jeu, criteria.jeu),
        (SyntheticPatient.phase, criteria.phase),
        (SyntheticPatient.statut_parcours, criteria.statut_parcours),
        (SyntheticPatient.organe, criteria.organe),
    ):
        if value:
            conditions.append(equals_ignoring_case(column, value))
    return conditions


class SyntheticPatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, criteria: SyntheticPatientCriteria) -> tuple[list[SyntheticPatient], int]:
        """Une page de patients synthétiques et le total de ceux qui correspondent aux filtres."""
        conditions = _conditions(criteria)

        total = await self._session.scalar(
            select(func.count()).select_from(SyntheticPatient).where(*conditions)
        )

        column = SORT_COLUMNS[criteria.sort_by]
        direction = column.desc() if criteria.sort_order is SortOrder.DESC else column.asc()
        rows = await self._session.scalars(
            select(SyntheticPatient)
            .where(*conditions)
            .order_by(direction.nulls_last(), SyntheticPatient.id)  # `id` : ordre stable
            .offset(criteria.offset)
            .limit(criteria.limit)
        )
        return list(rows), total or 0

    async def add_many_ignoring_existing(self, values: Sequence[Mapping[str, object]]) -> int:
        """Insère ceux dont l'id est absent ; renvoie le nombre réellement insérés.

        Leur `patient_id` doit être celui d'un patient existant (clé étrangère).
        """
        result = await self._session.execute(
            insert(SyntheticPatient).values(list(values)).on_conflict_do_nothing()
        )
        return result.rowcount
