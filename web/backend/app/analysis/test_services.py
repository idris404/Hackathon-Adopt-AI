import copy

import pytest
from pydantic import ValidationError

from app.analysis.schemas import AnalysisResultRead
from app.analysis.services import AnalysisService
from app.constants.analysis import DEMO_ANALYSIS_RESULT


def test_the_service_returns_the_demo_case() -> None:
    result = AnalysisService().get_result()

    assert isinstance(result, AnalysisResultRead)
    assert result.case_id == DEMO_ANALYSIS_RESULT["case_id"]
    assert result.synthetic is True


def test_a_result_that_is_not_synthetic_is_rejected() -> None:
    # Garde-fou : ce schéma sert une route publique, il ne doit pas pouvoir porter un cas réel.
    payload = copy.deepcopy(DEMO_ANALYSIS_RESULT)
    payload["synthetic"] = False

    with pytest.raises(ValidationError):
        AnalysisResultRead.model_validate(payload)


def test_a_result_missing_a_field_is_rejected() -> None:
    payload = copy.deepcopy(DEMO_ANALYSIS_RESULT)
    del payload["profile"]

    with pytest.raises(ValidationError):
        AnalysisResultRead.model_validate(payload)
