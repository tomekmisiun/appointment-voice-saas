from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.rate_limit import rate_limit
from app.core.config import settings
from app.core.redis import redis_client
from app.main import app


def clear_rate_limit_keys():
    keys = list(redis_client.scan_iter("rate_limit:*"))

    if keys:
        redis_client.delete(*keys)


@pytest.fixture(autouse=True)
def clean_rate_limit_keys():
    clear_rate_limit_keys()
    yield
    clear_rate_limit_keys()


def test_rate_limit_rejects_non_positive_overrides():
    with pytest.raises(ValueError):
        rate_limit(limit=0)

    with pytest.raises(ValueError):
        rate_limit(window_seconds=0)


def test_limited_endpoint_allows_requests_within_configured_limit(client):
    for _ in range(settings.rate_limit_default_limit):
        response = client.get("/health/limited")
        assert response.status_code == 200
        assert response.json() == {"message": "ok"}


def test_limited_endpoint_returns_429_after_configured_limit(client):
    for _ in range(settings.rate_limit_default_limit):
        response = client.get("/health/limited")
        assert response.status_code == 200

    response = client.get("/health/limited")

    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "Too many requests",
        }
    }


def test_limited_endpoint_sets_redis_ttl(client):
    response = client.get("/health/limited")

    keys = list(redis_client.scan_iter("rate_limit:*"))

    assert response.status_code == 200
    assert len(keys) == 1
    assert redis_client.ttl(keys[0]) > 0


def test_limited_endpoint_tracks_different_client_ips_separately():
    with TestClient(app, client=("203.0.113.1", 50000)) as first_client:
        for _ in range(settings.rate_limit_default_limit):
            response = first_client.get("/health/limited")
            assert response.status_code == 200

        response = first_client.get("/health/limited")
        assert response.status_code == 429

    with TestClient(app, client=("203.0.113.2", 50000)) as second_client:
        response = second_client.get("/health/limited")
        assert response.status_code == 200
