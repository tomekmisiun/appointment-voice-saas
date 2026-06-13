import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.core.ids import uuid7
from app.core.webhook_security import (
    WebhookSignatureError,
    compute_timestamped_hmac_signature,
    verify_timestamped_hmac_signature,
)
from app.models.webhook_event import WebhookEvent
from app.services.webhook_service import cleanup_old_webhook_events, persist_webhook_event
from app.services.idempotency_service import (
    build_scope_key,
    store_response,
    try_acquire_idempotency_lock,
)


WEBHOOK_PATH = "/api/v1/webhooks/inbound"
WEBHOOK_SECRET = "test-webhook-secret"


def current_timestamp() -> int:
    return int(time.time())


def build_webhook_payload(event_id: str | None = None):
    return {
        "provider": "payments",
        "event_id": event_id or f"evt_{uuid7().hex}",
        "event_type": "payment.succeeded",
        "payload": {"amount": 1000, "currency": "usd"},
    }


def build_webhook_headers(
    raw_body: bytes,
    idempotency_key: str = "key-1",
    *,
    timestamp: int | None = None,
    signature: str | None = None,
):
    effective_timestamp = current_timestamp() if timestamp is None else timestamp

    if signature is None:
        signature = compute_timestamped_hmac_signature(
            effective_timestamp,
            raw_body,
            WEBHOOK_SECRET,
        )

    return {
        "Idempotency-Key": idempotency_key,
        "X-Webhook-Timestamp": str(effective_timestamp),
        "X-Webhook-Signature": signature,
        "Content-Type": "application/json",
    }


def test_verify_timestamped_signature_accepts_valid_request():
    raw_body = b'{"provider":"payments"}'
    timestamp = current_timestamp()
    signature = compute_timestamped_hmac_signature(timestamp, raw_body, WEBHOOK_SECRET)

    verified_timestamp = verify_timestamped_hmac_signature(
        payload=raw_body,
        signature=signature,
        timestamp=timestamp,
        secret=WEBHOOK_SECRET,
        tolerance_seconds=300,
        now=timestamp,
    )

    assert verified_timestamp == timestamp


def test_verify_timestamped_signature_rejects_expired_timestamp():
    raw_body = b'{"provider":"payments"}'
    timestamp = current_timestamp() - 600
    signature = compute_timestamped_hmac_signature(timestamp, raw_body, WEBHOOK_SECRET)

    with pytest.raises(WebhookSignatureError, match="replay window"):
        verify_timestamped_hmac_signature(
            payload=raw_body,
            signature=signature,
            timestamp=timestamp,
            secret=WEBHOOK_SECRET,
            tolerance_seconds=300,
            now=current_timestamp(),
        )


def test_verify_timestamped_signature_accepts_stripe_style_header():
    raw_body = b'{"provider":"payments"}'
    timestamp = current_timestamp()
    signature = compute_timestamped_hmac_signature(timestamp, raw_body, WEBHOOK_SECRET)

    verified_timestamp = verify_timestamped_hmac_signature(
        payload=raw_body,
        signature=f"t={timestamp},v1={signature}",
        timestamp=None,
        secret=WEBHOOK_SECRET,
        tolerance_seconds=300,
        now=timestamp,
    )

    assert verified_timestamp == timestamp


def test_inbound_webhook_requires_signature(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    raw_body = json.dumps(build_webhook_payload()).encode("utf-8")

    response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers={
            "Idempotency-Key": "key-1",
            "X-Webhook-Timestamp": str(current_timestamp()),
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401


def test_inbound_webhook_requires_timestamp(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    raw_body = json.dumps(build_webhook_payload()).encode("utf-8")
    signature = compute_timestamped_hmac_signature(current_timestamp(), raw_body, WEBHOOK_SECRET)

    response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers={
            "Idempotency-Key": "key-1",
            "X-Webhook-Signature": signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Webhook timestamp is required"


def test_inbound_webhook_rejects_expired_timestamp(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    raw_body = json.dumps(build_webhook_payload()).encode("utf-8")
    expired_timestamp = current_timestamp() - 600

    response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers=build_webhook_headers(
            raw_body,
            idempotency_key="key-expired",
            timestamp=expired_timestamp,
        ),
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Webhook timestamp is outside the replay window"


def test_inbound_webhook_accepts_signed_event(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    payload = build_webhook_payload()
    raw_body = json.dumps(payload).encode("utf-8")

    response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers=build_webhook_headers(raw_body),
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted",
        "provider": "payments",
        "event_id": payload["event_id"],
    }


def test_inbound_webhook_rejects_replayed_event_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    payload = build_webhook_payload()
    raw_body = json.dumps(payload).encode("utf-8")
    headers = build_webhook_headers(raw_body, idempotency_key="key-2")

    first_response = client.post(WEBHOOK_PATH, content=raw_body, headers=headers)
    second_response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers=build_webhook_headers(raw_body, idempotency_key="key-3"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["status"] == "duplicate"


def test_inbound_webhook_returns_cached_response_for_same_idempotency_key(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    payload = build_webhook_payload()
    raw_body = json.dumps(payload).encode("utf-8")
    headers = build_webhook_headers(raw_body, idempotency_key="key-cache")

    first_response = client.post(WEBHOOK_PATH, content=raw_body, headers=headers)
    second_response = client.post(WEBHOOK_PATH, content=raw_body, headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()


def test_inbound_webhook_rejects_duplicate_in_flight_request(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )

    scope_key = build_scope_key("webhooks:inbound", "in-flight-key")
    assert try_acquire_idempotency_lock(scope_key) is True

    try:
        raw_body = json.dumps(build_webhook_payload()).encode("utf-8")

        response = client.post(
            WEBHOOK_PATH,
            content=raw_body,
            headers=build_webhook_headers(raw_body, idempotency_key="in-flight-key"),
        )
    finally:
        from app.services.idempotency_service import release_idempotency_lock

        release_idempotency_lock(scope_key)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Duplicate request is already in progress"


def test_store_response_returns_existing_record_on_unique_conflict(db):
    scope_key = build_scope_key("webhooks:inbound", "conflict-key")
    first_record = store_response(
        db,
        scope_key=scope_key,
        status_code=200,
        response_body={"status": "accepted", "provider": "payments", "event_id": "evt_1"},
    )
    second_record = store_response(
        db,
        scope_key=scope_key,
        status_code=200,
        response_body={"status": "accepted", "provider": "payments", "event_id": "evt_2"},
    )

    assert first_record.id == second_record.id


def test_cleanup_old_webhook_events_deletes_events_past_retention(db, monkeypatch):
    monkeypatch.setattr("app.services.webhook_service.settings.webhook_event_retention_days", 30)

    old_event = persist_webhook_event(
        db,
        provider="payments",
        event_id=f"evt_old_{uuid7().hex}",
        payload=b'{"provider":"payments"}',
    )
    old_event.received_at = datetime.now(timezone.utc) - timedelta(days=31)
    db.commit()

    recent_event = persist_webhook_event(
        db,
        provider="payments",
        event_id=f"evt_recent_{uuid7().hex}",
        payload=b'{"provider":"payments"}',
    )

    old_event_id = old_event.id
    recent_event_id = recent_event.id

    deleted_count = cleanup_old_webhook_events(db)

    assert deleted_count == 1
    assert db.query(WebhookEvent).filter(WebhookEvent.id == old_event_id).first() is None
    assert db.query(WebhookEvent).filter(WebhookEvent.id == recent_event_id).first() is not None


def test_inbound_webhook_rejects_oversized_payload(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    monkeypatch.setattr("app.core.config.settings.webhook_max_body_bytes", 32)
    raw_body = json.dumps(build_webhook_payload()).encode("utf-8")

    response = client.post(
        WEBHOOK_PATH,
        content=raw_body,
        headers=build_webhook_headers(raw_body),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_inbound_webhook_rate_limits_by_ip(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    monkeypatch.setattr("app.core.config.settings.webhook_ingress_rate_limit_limit", 1)
    monkeypatch.setattr(
        "app.core.config.settings.webhook_ingress_rate_limit_window_seconds",
        60,
    )
    raw_body = json.dumps(build_webhook_payload()).encode("utf-8")
    headers = build_webhook_headers(raw_body, idempotency_key=f"key-{uuid7().hex}")

    first_response = client.post(WEBHOOK_PATH, content=raw_body, headers=headers)

    second_body = json.dumps(build_webhook_payload()).encode("utf-8")
    second_response = client.post(
        WEBHOOK_PATH,
        content=second_body,
        headers=build_webhook_headers(second_body, idempotency_key=f"key-{uuid7().hex}"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429


def test_inbound_webhook_rate_limits_by_provider(client, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.webhook_signature_secret",
        WEBHOOK_SECRET,
    )
    monkeypatch.setattr("app.core.config.settings.webhook_provider_rate_limit_limit", 1)
    monkeypatch.setattr(
        "app.core.config.settings.webhook_provider_rate_limit_window_seconds",
        60,
    )

    first_body = json.dumps(build_webhook_payload(event_id=f"evt_{uuid7().hex}")).encode(
        "utf-8",
    )
    second_body = json.dumps(build_webhook_payload(event_id=f"evt_{uuid7().hex}")).encode(
        "utf-8",
    )

    first_response = client.post(
        WEBHOOK_PATH,
        content=first_body,
        headers=build_webhook_headers(first_body, idempotency_key=f"key-{uuid7().hex}"),
    )
    second_response = client.post(
        WEBHOOK_PATH,
        content=second_body,
        headers=build_webhook_headers(second_body, idempotency_key=f"key-{uuid7().hex}"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
