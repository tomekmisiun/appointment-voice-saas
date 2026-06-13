from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exception_handlers import unhandled_exception_handler
from app.core.redis import redis_client
from app.main import app
from tests.test_users import create_user_and_login, make_admin


def clear_rate_limit_keys():
    keys = list(redis_client.scan_iter("rate_limit:*"))

    if keys:
        redis_client.delete(*keys)


def test_unauthorized_error_uses_standard_envelope(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Not authenticated",
        }
    }


def test_forbidden_error_uses_standard_envelope(client, db):
    token, _ = create_user_and_login(db, client, "error-regular@example.com")

    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "Insufficient permissions",
        }
    }


def test_not_found_error_uses_standard_envelope(client, db):
    token, _ = create_user_and_login(db, client, "error-admin@example.com")
    make_admin(db, "error-admin@example.com")

    response = client.get(
        "/users/999999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "User not found",
        }
    }


def test_validation_error_uses_standard_envelope(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
        },
    )

    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["message"] == "Request validation failed"
    assert isinstance(data["error"]["details"], list)
    assert data["error"]["details"]


def test_unknown_route_error_uses_standard_envelope(client):
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Not Found",
        }
    }


@pytest.mark.anyio
async def test_unhandled_exception_uses_standard_envelope():
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/health/live"

    response = await unhandled_exception_handler(
        request,
        RuntimeError("secret internal details"),
    )

    assert response.status_code == 500
    assert response.body == (
        b'{"error":{"code":"internal_server_error",'
        b'"message":"An unexpected error occurred"}}'
    )


def test_rate_limit_error_uses_standard_envelope():
    clear_rate_limit_keys()

    with TestClient(app, client=("198.51.100.10", 50000)) as test_client:
        for _ in range(settings.rate_limit_default_limit):
            response = test_client.get("/health/limited")
            assert response.status_code == 200

        response = test_client.get("/health/limited")

    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "Too many requests",
        }
    }

    clear_rate_limit_keys()
