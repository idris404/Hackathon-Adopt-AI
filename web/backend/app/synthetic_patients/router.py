from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import current_active_user
from app.constants.synthetic_patients import (
    SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    SYNTHETIC_PATIENTS_ROUTER_TAG,
)
from app.core.pagination import Page
from app.synthetic_patients.dependencies import get_synthetic_patient_service
from app.synthetic_patients.schemas import SyntheticPatientListQuery, SyntheticPatientRead
from app.synthetic_patients.services import SyntheticPatientService

# Données de santé (même synthétiques) : toutes les routes du contexte exigent une session valide.
router = APIRouter(
    prefix=SYNTHETIC_PATIENTS_ROUTER_PREFIX,
    tags=[SYNTHETIC_PATIENTS_ROUTER_TAG],
    dependencies=[Depends(current_active_user)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Missing token or inactive user."}},
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
