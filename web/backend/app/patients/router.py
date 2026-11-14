import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.auth.dependencies import current_active_user
from app.constants.patients import PATIENTS_ROUTER_PREFIX, PATIENTS_ROUTER_TAG
from app.core.pagination import Page
from app.patients.dependencies import get_patient_service
from app.patients.schemas import PatientListQuery, PatientRead
from app.patients.services import PatientService

# Données de santé : toutes les routes du contexte exigent une session valide.
router = APIRouter(
    prefix=PATIENTS_ROUTER_PREFIX,
    tags=[PATIENTS_ROUTER_TAG],
    dependencies=[Depends(current_active_user)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Missing token or inactive user."}},
)


@router.get("", response_model=Page[PatientRead])
async def list_patients(
    query: Annotated[PatientListQuery, Query()],
    service: PatientService = Depends(get_patient_service),
) -> Page[PatientRead]:
    """Liste paginée, chaque patient avec ses tests sériques.

    Recherche (`search`), filtres, tri (`sort_by`, `sort_order`) : côté serveur.
    """
    return await service.list_patients(query)


@router.get(
    "/{id}",
    response_model=PatientRead,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Patient not found."}},
)
async def get_patient(
    # `{id}` : l'UUID du patient. Pas `patient_id`, qui est son identifiant fonctionnel (« HIS-00355 »).
    patient_uuid: Annotated[uuid.UUID, Path(alias="id")],
    service: PatientService = Depends(get_patient_service),
) -> PatientRead:
    return await service.get_patient(patient_uuid)
