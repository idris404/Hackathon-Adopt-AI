import uuid

from app.core.pagination import Page
from app.patients.services import PatientService
from app.synthetic_patients.repository import (
    SyntheticPatientCriteria,
    SyntheticPatientRepository,
)
from app.synthetic_patients.schemas import (
    SyntheticPatientListQuery,
    SyntheticPatientPageQuery,
    SyntheticPatientRead,
)


class SyntheticPatientService:
    def __init__(self, repository: SyntheticPatientRepository, patients: PatientService) -> None:
        self._repository = repository
        self._patients = patients  # API publique du contexte `patients`, pas son repository

    async def list_synthetic_patients(
        self, query: SyntheticPatientListQuery
    ) -> Page[SyntheticPatientRead]:
        criteria = self._criteria(
            query,
            search=query.search,
            patient_id=query.patient_id,
            sexe=query.sexe,
            jeu=query.jeu,
            phase=query.phase,
            statut_parcours=query.statut_parcours,
            organe=query.organe,
        )
        return await self._page(query, criteria)

    async def list_for_patient(
        self, patient_uuid: uuid.UUID, query: SyntheticPatientPageQuery
    ) -> Page[SyntheticPatientRead]:
        """Les patients synthétiques du patient d'`id` donné. Lève `PatientNotFoundError` si le
        patient n'existe pas : un patient inconnu n'est pas un patient sans patient synthétique.

        L'URL désigne le patient par son `id` (UUID) ; la liaison, elle, se fait par son `patient_id`.
        """
        patient = await self._patients.get_patient(patient_uuid)
        return await self._page(query, self._criteria(query, patient_id=patient.patient_id))

    @staticmethod
    def _criteria(query: SyntheticPatientPageQuery, **filters: object) -> SyntheticPatientCriteria:
        return SyntheticPatientCriteria(
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            offset=(query.page - 1) * query.page_size,
            limit=query.page_size,
            **filters,
        )

    async def _page(
        self, query: SyntheticPatientPageQuery, criteria: SyntheticPatientCriteria
    ) -> Page[SyntheticPatientRead]:
        synthetic_patients, total = await self._repository.find(criteria)
        return Page[SyntheticPatientRead](
            items=[SyntheticPatientRead.model_validate(item) for item in synthetic_patients],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
