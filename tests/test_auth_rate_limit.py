from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.redis import redis_client
from app.db.session import get_db
from app.main import app


def test_login_allows_requests_within_configured_limit(client):
    payload = {"email": "rate-limit-login@example.com", "password": "wrong-password"}

    for _ in range(settings.auth_login_rate_limit_limit):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401

    response = client.post("/auth/login", json=payload)
    assert response.status_code == 429


def test_login_rate_limit_sets_redis_ttl(client):
    client.post(
        "/auth/login",
        json={"email": "ttl-login@example.com", "password": "wrong-password"},
    )

    keys = list(redis_client.scan_iter("rate_limit:auth_login:*"))
    assert len(keys) == 1
    assert redis_client.ttl(keys[0]) > 0


def test_login_rate_limit_tracks_different_client_ips_separately(db):
    payload = {"email": "ip-login@example.com", "password": "wrong-password"}

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app, client=("203.0.113.10", 50000)) as first_client:
            for _ in range(settings.auth_login_rate_limit_limit):
                response = first_client.post("/auth/login", json=payload)
                assert response.status_code == 401

            response = first_client.post("/auth/login", json=payload)
            assert response.status_code == 429

        with TestClient(app, client=("203.0.113.11", 50000)) as second_client:
            response = second_client.post("/auth/login", json=payload)
            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_register_returns_429_after_configured_limit(client):
    for index in range(settings.auth_register_rate_limit_limit):
        response = client.post(
            "/auth/register",
            json={
                "email": f"register-limit-{index}@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200

    response = client.post(
        "/auth/register",
        json={"email": "register-limit-blocked@example.com", "password": "password123"},
    )
    assert response.status_code == 429


def test_refresh_returns_429_after_configured_limit(client):
    client.post(
        "/auth/register",
        json={"email": "refresh-limit@example.com", "password": "password123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "refresh-limit@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    for _ in range(settings.auth_refresh_rate_limit_limit):
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        refresh_token = response.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 429


def test_logout_returns_429_after_configured_limit(client):
    for _ in range(settings.auth_logout_rate_limit_limit):
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/logout",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 429
