from fastapi.testclient import TestClient

from app.core.config import get_settings

PREFLIGHT_HEADERS = {"Access-Control-Request-Method": "POST"}


def preflight(client: TestClient, origin: str):
    return client.options(
        "/auth/login", headers={"Origin": origin, **PREFLIGHT_HEADERS}
    )


def test_the_frontend_origin_may_send_credentials(client: TestClient) -> None:
    origin = get_settings().frontend_url

    response = preflight(client, origin)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_another_origin_is_not_allowed(client: TestClient) -> None:
    response = preflight(client, "https://evil.example")

    # Sans `access-control-allow-origin`, le navigateur bloque la requête.
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
