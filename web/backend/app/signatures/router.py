from fastapi import APIRouter, Depends, status

from app.auth.dependencies import current_active_user
from app.constants.signatures import (
    SIGN_QUEUE_PATH,
    SIGNATURES_ROUTER_PREFIX,
    SIGNATURES_ROUTER_TAG,
)
from app.signatures.dependencies import get_signature_service
from app.signatures.schemas import SignatureCreate, SignatureRead, SignQueueRead
from app.signatures.services import SignatureService
from app.users.entity import User

# Données de santé : toutes les routes du contexte exigent une session valide.
router = APIRouter(
    prefix=SIGNATURES_ROUTER_PREFIX,
    tags=[SIGNATURES_ROUTER_TAG],
    dependencies=[Depends(current_active_user)],
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Missing token or inactive user."}},
)


@router.get(SIGN_QUEUE_PATH, response_model=SignQueueRead)
async def sign_queue(service: SignatureService = Depends(get_signature_service)) -> SignQueueRead:
    """Les cas simples à valider : profil sérique constant, historique court, pas encore signés."""
    return await service.queue()


@router.post(
    "",
    response_model=SignatureRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Patient not found."},
        status.HTTP_409_CONFLICT: {"description": "Patient already signed."},
    },
)
async def sign_patient(
    body: SignatureCreate,
    user: User = Depends(current_active_user),
    service: SignatureService = Depends(get_signature_service),
) -> SignatureRead:
    return await service.sign(body.patient_id, user.id)
