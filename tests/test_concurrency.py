import time
from concurrent.futures import ThreadPoolExecutor

from app.core.domain_errors import UnauthorizedError

from app.core.ids import uuid7
from app.core.job_queue import dequeue_job, enqueue_job
from app.core.redis import redis_client, revoke_refresh_token
from app.services.auth_service import rotate_refresh_token
from app.services.health_service import check_database, get_readiness
from app.services.idempotency_service import (
    build_scope_key,
    release_idempotency_lock,
    store_response,
    try_acquire_idempotency_lock,
)
from app.services.storage_service import build_object_key
from tests.database import TestingSessionLocal


def test_concurrent_idempotency_lock_acquires_once():
    scope_key = build_scope_key("concurrency-test", f"lock-{uuid7().hex}")

    try:

        def acquire_lock() -> bool:
            return try_acquire_idempotency_lock(scope_key)

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(lambda _: acquire_lock(), range(12)))

        assert results.count(True) == 1
        assert results.count(False) == 11
    finally:
        release_idempotency_lock(scope_key)


def test_concurrent_store_response_persists_single_record():
    scope_key = build_scope_key("concurrency-test", f"store-{uuid7().hex}")

    def store_once(index: int) -> int:
        session = TestingSessionLocal()

        try:
            record = store_response(
                session,
                scope_key=scope_key,
                status_code=200,
                response_body={"index": index},
            )
            return record.id
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=10) as executor:
        record_ids = list(executor.map(store_once, range(10)))

    assert len(set(record_ids)) == 1


def test_concurrent_refresh_token_rotation_allows_single_success(client):
    email = f"refresh-race-{uuid7().hex}@example.com"
    register_data = {"email": email, "password": "password123"}

    client.post("/auth/register", json=register_data)
    login_response = client.post("/auth/login", json=register_data)
    refresh_token = login_response.json()["refresh_token"]

    def rotate_once() -> str | int:
        session = TestingSessionLocal()

        try:
            rotate_refresh_token(session, refresh_token)
            return "success"
        except UnauthorizedError as exc:
            return exc.status_code
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: rotate_once(), range(10)))

    assert results.count("success") == 1
    assert results.count(401) == 9


def test_revoke_refresh_token_require_new_is_exclusive():
    jti = uuid7().hex
    expires_at = int(time.time()) + 3600

    assert revoke_refresh_token(jti, expires_at, require_new=True) is True
    assert revoke_refresh_token(jti, expires_at, require_new=True) is False


def test_concurrent_dequeue_assigns_each_job_once():
    queue_name = f"concurrency-jobs-{uuid7().hex}"
    processing_queue_name = f"{queue_name}:processing"
    job_count = 12

    for index in range(job_count):
        enqueue_job(
            "concurrency_probe",
            {"index": index},
            redis=redis_client,
            queue_name=queue_name,
        )

    def dequeue_once():
        return dequeue_job(
            redis=redis_client,
            queue_name=queue_name,
            processing_queue_name=processing_queue_name,
            timeout_seconds=1,
        )

    with ThreadPoolExecutor(max_workers=job_count) as executor:
        dequeued_jobs = list(executor.map(lambda _: dequeue_once(), range(job_count)))

    assert all(job is not None for job in dequeued_jobs)
    assert len({job.id for job in dequeued_jobs}) == job_count


def test_concurrent_rate_limit_counter_stays_within_window():
    key = f"rate_limit:concurrency-{uuid7().hex}"
    limit = 5

    try:

        def increment_counter() -> bool:
            current_count = redis_client.incr(key)

            if current_count == 1:
                redis_client.expire(key, 60)

            return current_count <= limit

        with ThreadPoolExecutor(max_workers=20) as executor:
            allowed = list(executor.map(lambda _: increment_counter(), range(20)))

        assert allowed.count(True) == limit
        assert allowed.count(False) == 20 - limit
    finally:
        redis_client.delete(key)


def test_build_object_key_generates_unique_keys_under_concurrency():
    tenant_id = 1
    owner_id = 2

    def build_key(index: int) -> str:
        return build_object_key(tenant_id, owner_id, f"invoice-{index}.pdf")

    with ThreadPoolExecutor(max_workers=20) as executor:
        object_keys = list(executor.map(build_key, range(20)))

    assert len(set(object_keys)) == 20


def test_readiness_checks_survive_slow_dependency_latency(db, monkeypatch):
    def slow_database_check(session):
        time.sleep(0.05)
        return check_database(session)

    monkeypatch.setattr(
        "app.services.health_service.check_database",
        slow_database_check,
    )

    def check_readiness_once() -> str:
        session = TestingSessionLocal()

        try:
            return get_readiness(session).status
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(lambda _: check_readiness_once(), range(8)))

    assert statuses == ["ok"] * 8
