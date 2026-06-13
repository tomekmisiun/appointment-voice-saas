from app.core.cache import (
    get_cache_version,
    get_json_cache,
    increment_cache_version,
    set_json_cache,
)
from app.core.ids import uuid7
from app.services.user_service import (
    build_users_list_cache_key,
    build_users_list_cache_version_key,
    invalidate_users_list_cache,
)


def test_get_cache_version_defaults_to_zero_when_missing():
    version_key = f"test-cache-version:{uuid7().hex}"

    assert get_cache_version(version_key) == 0


def test_increment_cache_version_starts_at_one():
    version_key = f"test-cache-version:{uuid7().hex}"

    assert increment_cache_version(version_key) == 1
    assert get_cache_version(version_key) == 1
    assert increment_cache_version(version_key) == 2


def test_invalidate_users_list_cache_bumps_version_key():
    tenant_id = int(uuid7().hex[:8], 16)
    version_key = build_users_list_cache_version_key(tenant_id)
    cache_key = build_users_list_cache_key(
        tenant_id=tenant_id,
        skip=0,
        limit=10,
        sort_by="id",
        sort_order="asc",
        role=None,
        is_active=None,
        search=None,
        search_mode="prefix",
        cursor=None,
    )

    cached_payload = {"items": [{"id": 1}], "next_cursor": None}
    set_json_cache(cache_key, cached_payload, ttl_seconds=60)
    assert get_json_cache(cache_key) == cached_payload

    invalidate_users_list_cache(tenant_id)

    assert get_cache_version(version_key) == 1
    assert get_json_cache(cache_key) == cached_payload

    new_cache_key = build_users_list_cache_key(
        tenant_id=tenant_id,
        skip=0,
        limit=10,
        sort_by="id",
        sort_order="asc",
        role=None,
        is_active=None,
        search=None,
        search_mode="prefix",
        cursor=None,
    )

    assert new_cache_key != cache_key
    assert get_json_cache(new_cache_key) is None
