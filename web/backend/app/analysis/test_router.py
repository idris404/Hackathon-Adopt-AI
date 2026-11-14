from fastapi.testclient import TestClient

from app.conftest import ANALYSIS_URL
from app.constants.analysis import ANALYSIS_RESULT_PATH, DEMO_ANALYSIS_RESULT

RESULT_URL = f"{ANALYSIS_URL}{ANALYSIS_RESULT_PATH}"


def test_the_result_is_public_and_needs_no_session(client: TestClient) -> None:
    # `client` n'est pas connecté : ni cookie, ni en-tête d'autorisation.
    response = client.get(RESULT_URL)

    assert response.status_code == 200
    assert not client.cookies


def test_the_result_is_returned_exactly_as_the_model_outputs_it(client: TestClient) -> None:
    body = client.get(RESULT_URL).json()

    # Même champs, même valeurs, même ordre : le schéma de sortie n'omet ni ne transforme rien.
    assert body == DEMO_ANALYSIS_RESULT
    assert list(body) == list(DEMO_ANALYSIS_RESULT)
    assert list(body["profile"]) == list(DEMO_ANALYSIS_RESULT["profile"])
    assert list(body["provenance"]) == list(DEMO_ANALYSIS_RESULT["provenance"])


def test_the_public_result_is_always_synthetic(client: TestClient) -> None:
    body = client.get(RESULT_URL).json()

    assert body["synthetic"] is True
    assert body["provenance"]["source_record_copied"] is False


def test_the_result_is_read_only(client: TestClient) -> None:
    assert client.post(RESULT_URL).status_code == 405
    assert client.delete(RESULT_URL).status_code == 405
