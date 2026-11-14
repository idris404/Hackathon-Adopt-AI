from app.core.pagination import Page
from app.synthetic_patients.repository import (
    SyntheticPatientCriteria,
    SyntheticPatientRepository,
)
from app.synthetic_patients.schemas import SyntheticPatientListQuery, SyntheticPatientRead


class SyntheticPatientService:
    def __init__(self, repository: SyntheticPatientRepository) -> None:
        self._repository = repository

    async def list_synthetic_patients(
        self, query: SyntheticPatientListQuery
    ) -> Page[SyntheticPatientRead]:
        criteria = SyntheticPatientCriteria(
            search=query.search,
            patient_id=query.patient_id,
            sexe=query.sexe,
            jeu=query.jeu,
            phase=query.phase,
            statut_parcours=query.statut_parcours,
            organe=query.organe,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            offset=(query.page - 1) * query.page_size,
            limit=query.page_size,
        )
        synthetic_patients, total = await self._repository.find(criteria)
        return Page[SyntheticPatientRead](
            items=[SyntheticPatientRead.model_validate(item) for item in synthetic_patients],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
