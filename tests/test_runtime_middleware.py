from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.runtime import configure_runtime_middleware


def build_runtime_test_client(settings: Settings) -> TestClient:
    app = FastAPI()
    configure_runtime_middleware(app, settings)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return TestClient(app)


def test_security_headers_are_added_to_responses(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Permissions-Policy" in response.headers


def test_hsts_header_is_added_when_enabled():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        security_headers_enabled=True,
        hsts_enabled=True,
        hsts_max_age_seconds=86400,
    )
    client = build_runtime_test_client(settings)

    response = client.get("/health")

    assert response.status_code == 200
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=86400; includeSubDomains"
    )


def test_trusted_host_middleware_rejects_unknown_host():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        trusted_hosts_enabled=True,
        trusted_hosts="api.example.test",
    )
    client = build_runtime_test_client(settings)

    response = client.get("/health", headers={"Host": "evil.example.test"})

    assert response.status_code == 400


def test_trusted_host_middleware_allows_configured_host():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        trusted_hosts_enabled=True,
        trusted_hosts="api.example.test",
    )
    client = build_runtime_test_client(settings)

    response = client.get("/health", headers={"Host": "api.example.test"})

    assert response.status_code == 200


def test_cors_middleware_allows_configured_origin():
    settings = Settings(
        _env_file=None,
        secret_key="development-secret",
        cors_enabled=True,
        cors_allow_origins="https://app.example.test",
    )
    client = build_runtime_test_client(settings)

    response = client.get(
        "/health",
        headers={"Origin": "https://app.example.test"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
