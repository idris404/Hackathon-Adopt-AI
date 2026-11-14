from app.analysis.schemas import AnalysisResultRead
from app.constants.analysis import DEMO_ANALYSIS_RESULT


class AnalysisService:
    """Fournit le résultat d'analyse.

    Pour l'instant, c'est le cas synthétique de démonstration. Le branchement sur le vrai modèle
    se fera ici, sans toucher au router.
    """

    def get_result(self) -> AnalysisResultRead:
        return AnalysisResultRead.model_validate(DEMO_ANALYSIS_RESULT)
