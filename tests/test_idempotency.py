from datetime import datetime, timedelta, timezone

import pytest

from app.core.domain_errors import BadRequestError

from app.core.ids import uuid7
from app.models.idempotency_record import IdempotencyRecord
from app.services.idempotency_service import (
    build_scope_key,
    cleanup_expired_idempotency_records,
    get_cached_response,
    store_response,
)


def test_build_scope_key_normalizes_input():
    first_scope = build_scope_key("webhooks:inbound", "  key-1  ")
    second_scope = build_scope_key("webhooks:inbound", "key-1")

    assert first_scope == second_scope


def test_build_scope_key_requires_non_empty_key():
    with pytest.raises(BadRequestError) as exc_info:
        build_scope_key("webhooks:inbound", "   ")

    assert exc_info.value.status_code == 400


def test_get_cached_response_ignores_expired_records(db):
    scope_key = build_scope_key("webhooks:inbound", "expired-key")
    expired_record = store_response(
        db,
        scope_key=scope_key,
        status_code=200,
        response_body={"status": "accepted"},
    )
    expired_record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert get_cached_response(db, scope_key) is None


def test_cleanup_expired_idempotency_records_deletes_only_expired_rows(db):
    suffix = uuid7().hex
    active_scope = build_scope_key("webhooks:inbound", f"active-key-{suffix}")
    expired_scope = build_scope_key("webhooks:inbound", f"expired-key-{suffix}")

    store_response(
        db,
        scope_key=active_scope,
        status_code=200,
        response_body={"status": "accepted"},
    )
    expired_record = store_response(
        db,
        scope_key=expired_scope,
        status_code=200,
        response_body={"status": "accepted"},
    )
    expired_record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    assert (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.scope_key == expired_scope)
        .count()
        == 1
    )

    cleanup_expired_idempotency_records(db)

    assert (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.scope_key == expired_scope)
        .count()
        == 0
    )
    assert get_cached_response(db, active_scope) is not None
