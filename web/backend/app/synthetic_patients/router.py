import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.auth.dependencies import current_active_user
from app.constants.synthetic_patients import (
    PATIENT_SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    SYNTHETIC_PATIENTS_ROUTER_TAG,
)
from app.core.pagination import Page
from app.synthetic_patients.dependencies import get_synthetic_patient_service
from app.synthetic_patients.schemas import (
    SyntheticPatientListQuery,
    SyntheticPatientPageQuery,
    SyntheticPatientRead,
)
from app.synthetic_patients.services import SyntheticPatientService

# Données de santé (même synthétiques) : toutes les routes du contexte exigent une session valide.
UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing token or inactive user."}
}

router = APIRouter(
    prefix=SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    tags=[SYNTHETIC_PATIENTS_ROUTER_TAG],
    dependencies=[Depends(current_active_user)],
    responses=UNAUTHORIZED_RESPONSE,
)

# /patients/{patient_id}/synthetic-patients : même contexte, mais l'URL commence par le patient.
patient_router = APIRouter(
    prefix=PATIENT_SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    tags=[SYNTHETIC_PATIENTS_ROUTER_TAG],
    dependencies=[Depends(current_active_user)],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.get("", response_model=Page[SyntheticPatientRead])
async def list_synthetic_patients(
    query: Annotated[SyntheticPatientListQuery, Query()],
    service: SyntheticPatientService = Depends(get_synthetic_patient_service),
) -> Page[SyntheticPatientRead]:
    """Liste paginée. Recherche (`search`), filtres, tri (`sort_by`, `sort_order`) : côté serveur.

    `patient_id` renvoie les patients synthétiques d'un patient.
    """
    return await service.list_synthetic_patients(query)


@patient_router.get(
    "",
    response_model=Page[SyntheticPatientRead],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Patient not found."}},
)
async def list_synthetic_patients_of_patient(
    # `{id}` : l'UUID du patient. Pas `patient_id`, qui est son identifiant fonctionnel (« SYN-0001 »).
    patient_uuid: Annotated[uuid.UUID, Path(alias="id")],
    query: Annotated[SyntheticPatientPageQuery, Query()],
    service: SyntheticPatientService = Depends(get_synthetic_patient_service),
) -> Page[SyntheticPatientRead]:
    """Les patients synthétiques d'un patient, paginés (un patient peut en avoir plusieurs).

    404 si le patient n'existe pas ; une page vide s'il n'en a aucun.
    """
    return await service.list_for_patient(patient_uuid, query)
