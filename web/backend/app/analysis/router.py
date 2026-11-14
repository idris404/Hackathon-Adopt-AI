from fastapi import APIRouter, Depends

from app.analysis.schemas import AnalysisResultRead
from app.analysis.services import AnalysisService
from app.constants.analysis import (
    ANALYSIS_RESULT_PATH,
    ANALYSIS_ROUTER_PREFIX,
    ANALYSIS_ROUTER_TAG,
)

router = APIRouter(prefix=ANALYSIS_ROUTER_PREFIX, tags=[ANALYSIS_ROUTER_TAG])


@router.get(ANALYSIS_RESULT_PATH, response_model=AnalysisResultRead)
async def get_result(service: AnalysisService = Depends()) -> AnalysisResultRead:
    """Résultat d'analyse. Route publique : pas de session requise, données synthétiques seulement."""
    return service.get_result()
