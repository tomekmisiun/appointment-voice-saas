from app.api.v1 import API_V1_PREFIX


V1_ROUTE_CHECKS = [
    ("POST", f"{API_V1_PREFIX}/auth/register", 422),
    ("POST", f"{API_V1_PREFIX}/auth/login", 422),
    ("GET", f"{API_V1_PREFIX}/auth/me", 401),
    ("POST", f"{API_V1_PREFIX}/auth/refresh", 422),
    ("POST", f"{API_V1_PREFIX}/auth/logout", 422),
    ("POST", f"{API_V1_PREFIX}/auth/password-reset/request", 422),
    ("POST", f"{API_V1_PREFIX}/auth/password-reset/confirm", 422),
    ("GET", f"{API_V1_PREFIX}/users/", 401),
    ("GET", f"{API_V1_PREFIX}/admin", 401),
    ("GET", f"{API_V1_PREFIX}/admin/audit-logs", 401),
    ("GET", f"{API_V1_PREFIX}/admin/tenants", 401),
    ("POST", f"{API_V1_PREFIX}/admin/tenants", 401),
    ("POST", f"{API_V1_PREFIX}/files/upload", 401),
]

LEGACY_ROUTE_CHECKS = [
    ("POST", "/auth/register", 422),
    ("GET", "/users/", 401),
    ("GET", "/admin", 401),
    ("POST", "/files/upload", 401),
]


def test_api_v1_routes_are_available(client):
    for method, path, expected_status in V1_ROUTE_CHECKS:
        response = client.request(method, path)

        assert response.status_code == expected_status, (
            f"{method} {path} returned {response.status_code}"
        )


def test_legacy_routes_remain_available_for_backward_compatibility(client):
    for method, path, expected_status in LEGACY_ROUTE_CHECKS:
        response = client.request(method, path)

        assert response.status_code == expected_status, (
            f"{method} {path} returned {response.status_code}"
        )


def test_legacy_routes_are_not_mounted_when_disabled(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.main import include_application_routers

    monkeypatch.setattr("app.core.config.settings.legacy_routes_enabled", False)

    test_app = FastAPI()
    include_application_routers(test_app)
    test_client = TestClient(test_app)

    for method, path, _expected_status in LEGACY_ROUTE_CHECKS:
        response = test_client.request(method, path)
        assert response.status_code == 404, f"{method} {path} should be unavailable"

    openapi_paths = test_client.get("/openapi.json").json()["paths"]
    assert "/auth/login" not in openapi_paths
    assert "/users/" not in openapi_paths


def test_openapi_marks_legacy_routes_as_deprecated(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert paths["/auth/login"]["post"]["deprecated"] is True
    assert paths["/users/"]["get"]["deprecated"] is True
    assert paths[f"{API_V1_PREFIX}/auth/login"]["post"].get("deprecated") is not True


def test_openapi_documents_api_v1_paths(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert f"{API_V1_PREFIX}/auth/login" in paths
    assert f"{API_V1_PREFIX}/users/" in paths
    assert "/health" in paths
    assert "/metrics" in paths
