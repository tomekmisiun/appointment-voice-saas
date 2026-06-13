from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.cache import get_json_cache, set_json_cache
from app.core.ids import uuid7
from tests.test_users import auth_headers, create_user_and_login, make_admin


def test_admin_list_users_degrades_when_cache_read_fails(
    db,
    client,
    monkeypatch,
):
    email = f"redis-read-fail-{uuid7().hex}@example.com"
    token, _ = create_user_and_login(db, client, email)
    make_admin(db, email)

    class UnavailableRedis:
        def get(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

        def set(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

    monkeypatch.setattr("app.core.cache.redis_client", UnavailableRedis())

    response = client.get("/users/", headers=auth_headers(token))

    assert response.status_code == 200


def test_admin_list_users_degrades_when_cache_write_fails(
    db,
    client,
    monkeypatch,
):
    email = f"redis-write-fail-{uuid7().hex}@example.com"
    token, _ = create_user_and_login(db, client, email)
    make_admin(db, email)

    class UnavailableRedis:
        def get(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

    monkeypatch.setattr("app.core.cache.redis_client", UnavailableRedis())

    response = client.get("/users/", headers=auth_headers(token))

    assert response.status_code == 200


def test_users_list_cache_misses_return_consistent_results(db, client, monkeypatch):
    email = f"cache-stampede-{uuid7().hex}@example.com"
    token, _ = create_user_and_login(db, client, email)
    make_admin(db, email)
    headers = auth_headers(token)

    monkeypatch.setattr(
        "app.services.user_service.get_json_cache",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.user_service.set_json_cache",
        lambda *args, **kwargs: None,
    )

    first_response = client.get("/users/", headers=headers)
    second_response = client.get("/users/", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_limited_endpoint_returns_service_unavailable_when_redis_is_unavailable(
    client,
    monkeypatch,
):
    class UnavailableRedis:
        def incr(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

        def expire(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

    monkeypatch.setattr(
        "app.api.dependencies.rate_limit.redis_client",
        UnavailableRedis(),
    )

    response = client.get("/health/limited")

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Service temporarily unavailable"


def test_json_cache_helpers_degrade_when_redis_is_unavailable(monkeypatch):
    class UnavailableRedis:
        def get(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

        def set(self, *args, **kwargs):
            raise RedisConnectionError("redis unavailable")

    cache_key = f"ops-redis-smoke:{uuid7().hex}"
    unavailable_redis = UnavailableRedis()

    set_json_cache(
        cache_key,
        {"ok": True},
        ttl_seconds=30,
        redis=unavailable_redis,
    )
    assert get_json_cache(cache_key, redis=unavailable_redis) is None


def test_json_cache_helpers_require_working_redis():
    cache_key = f"ops-redis-smoke:{uuid7().hex}"

    set_json_cache(cache_key, {"ok": True}, ttl_seconds=30)

    assert get_json_cache(cache_key) == {"ok": True}
