import uuid
from collections.abc import Collection

from app.core.pagination import Page
from app.patients.exceptions import PatientNotFoundError
from app.patients.repository import PatientCriteria, PatientRepository
from app.patients.schemas import PatientListQuery, PatientRead


class PatientService:
    def __init__(self, repository: PatientRepository) -> None:
        self._repository = repository

    async def list_patients(self, query: PatientListQuery) -> Page[PatientRead]:
        criteria = PatientCriteria(
            search=query.search,
            gender=query.gender,
            city=query.city,
            country=query.country,
            birth_from=query.birth_from,
            birth_to=query.birth_to,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            offset=(query.page - 1) * query.page_size,
            limit=query.page_size,
        )
        patients, total = await self._repository.find(criteria)
        return Page[PatientRead](
            items=[PatientRead.model_validate(patient) for patient in patients],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def existing_patient_ids(self, patient_ids: Collection[str]) -> set[str]:
        """Parmi ces `patient_id`, ceux qui sont des patients. API publique du contexte : les
        autres contextes (patients synthétiques) s'en servent sans toucher à son repository."""
        return await self._repository.existing_patient_ids(patient_ids)

    async def get_patient(self, patient_id: uuid.UUID) -> PatientRead:
        patient = await self._repository.get_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError
        return PatientRead.model_validate(patient)
