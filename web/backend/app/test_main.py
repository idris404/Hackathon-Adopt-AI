import pytest
from fastapi.testclient import TestClient

from app.conftest import AUTH_URL, USERS_URL
from app.constants.http import API_PREFIX, API_V1_PREFIX
from app.core.config import get_settings
from app.main import app

PREFLIGHT_HEADERS = {"Access-Control-Request-Method": "POST"}


def preflight(client: TestClient, origin: str):
    return client.options(
        f"{AUTH_URL}/login", headers={"Origin": origin, **PREFLIGHT_HEADERS}
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


def test_every_documented_route_lives_under_the_api_version_prefix() -> None:
    paths = app.openapi()["paths"]

    assert paths
    assert all(path.startswith(f"{API_V1_PREFIX}/") for path in paths)


def test_the_versioned_routes_are_reachable(client: TestClient) -> None:
    # 401 et non 404 : la route existe, elle exige simplement une session.
    assert client.get(f"{USERS_URL}/me").status_code == 401


@pytest.mark.parametrize("path", ["/auth/login", "/auth/register", "/users/me"])
def test_routes_are_not_exposed_without_the_version_prefix(
    client: TestClient, path: str
) -> None:
    assert client.post(path).status_code == 404
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("version", ["v0", "v2"])
def test_an_unknown_api_version_is_not_found(client: TestClient, version: str) -> None:
    assert client.get(f"{API_PREFIX}/{version}/users/me").status_code == 404
