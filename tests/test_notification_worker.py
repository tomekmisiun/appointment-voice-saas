"""Tests for the notification outbox worker (AVS-E006, AVS-E007, AVS-E008)."""

import pytest

from datetime import datetime, timezone

from app.core.job_queue import Job
from app.core.sms import SmsMessage, SmsSendResult
from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.notification_service import (
    MAX_NOTIFICATION_ATTEMPTS,
    SEND_NOTIFICATION_JOB,
    SmsDeliveryError,
    send_notification_in_worker,
)
from app.services.sms_provider import FakeSmsProvider
from app.worker import handle_job


def _create_pending_intent(db, **overrides):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(
        db, tenant_id=tenant.id, name="Notify Worker Salon", timezone="Europe/Warsaw"
    )

    intent = NotificationOutbox(
        tenant_id=tenant.id,
        business_id=overrides.get("business_id", business.id),
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.BOOKING_CONFIRMATION,
        recipient_phone=overrides.get("recipient_phone", "+48600100200"),
        body=overrides.get("body", "Your booking is confirmed."),
        status=overrides.get("status", NotificationStatus.PENDING),
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return intent


def test_send_notification_in_worker_marks_intent_sent_on_success(db):
    intent = _create_pending_intent(db)
    provider = FakeSmsProvider()

    send_notification_in_worker(db, notification_id=intent.id, sms_provider=provider)

    db.refresh(intent)
    assert intent.status == NotificationStatus.SENT
    assert intent.attempts == 1
    assert intent.last_error is None
    assert intent.sent_at is not None
    assert provider.sent == [SmsMessage(to=intent.recipient_phone, body=intent.body)]


class _FailingSmsProvider:
    def send(self, message: SmsMessage) -> SmsSendResult:
        del message
        return SmsSendResult(success=False, error="provider_unavailable")


def test_send_notification_in_worker_observes_success_metric(db, monkeypatch):
    intent = _create_pending_intent(db)
    observed = []
    monkeypatch.setattr(
        "app.services.notification_service.observe_sms_provider_request",
        lambda **kwargs: observed.append(kwargs),
    )

    send_notification_in_worker(db, notification_id=intent.id, sms_provider=FakeSmsProvider())

    assert observed == [{"provider": "fake", "status": "success"}]


def test_send_notification_in_worker_observes_failure_metric_with_fallback_name(db, monkeypatch):
    intent = _create_pending_intent(db)
    observed = []
    monkeypatch.setattr(
        "app.services.notification_service.observe_sms_provider_request",
        lambda **kwargs: observed.append(kwargs),
    )

    with pytest.raises(SmsDeliveryError):
        send_notification_in_worker(db, notification_id=intent.id, sms_provider=_FailingSmsProvider())

    # _FailingSmsProvider has no .name attribute; falls back to the class name.
    assert observed == [{"provider": "_FailingSmsProvider", "status": "failure"}]


def test_send_notification_in_worker_keeps_pending_and_raises_on_first_failure(db):
    intent = _create_pending_intent(db)

    with pytest.raises(SmsDeliveryError):
        send_notification_in_worker(
            db, notification_id=intent.id, sms_provider=_FailingSmsProvider()
        )

    db.refresh(intent)
    assert intent.status == NotificationStatus.PENDING
    assert intent.attempts == 1
    assert intent.last_error == "provider_unavailable"
    assert intent.sent_at is None


def test_send_notification_in_worker_marks_failed_after_max_attempts(db):
    intent = _create_pending_intent(db)
    intent.attempts = MAX_NOTIFICATION_ATTEMPTS - 1
    db.commit()

    # No exception raised — terminal failure should not trigger another worker retry
    send_notification_in_worker(
        db, notification_id=intent.id, sms_provider=_FailingSmsProvider()
    )

    db.refresh(intent)
    assert intent.status == NotificationStatus.FAILED
    assert intent.attempts == MAX_NOTIFICATION_ATTEMPTS
    assert intent.last_error == "provider_unavailable"


def test_send_notification_in_worker_updates_last_error_on_each_attempt(db):
    intent = _create_pending_intent(db)
    provider = _FailingSmsProvider()

    for expected_attempts in range(1, MAX_NOTIFICATION_ATTEMPTS):
        with pytest.raises(SmsDeliveryError):
            send_notification_in_worker(db, notification_id=intent.id, sms_provider=provider)
        db.refresh(intent)
        assert intent.attempts == expected_attempts
        assert intent.last_error == "provider_unavailable"
        assert intent.status == NotificationStatus.PENDING


def test_send_notification_in_worker_is_idempotent_for_non_pending_intents(db):
    intent = _create_pending_intent(db, status=NotificationStatus.SENT)
    intent.sent_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.commit()
    provider = FakeSmsProvider()

    send_notification_in_worker(db, notification_id=intent.id, sms_provider=provider)

    db.refresh(intent)
    assert intent.status == NotificationStatus.SENT
    assert intent.attempts == 0
    assert provider.sent == []


def test_send_notification_in_worker_handles_missing_intent(db):
    send_notification_in_worker(db, notification_id=999999, sms_provider=FakeSmsProvider())


def test_handle_job_dispatches_send_notification_job(db, monkeypatch):
    intent = _create_pending_intent(db)
    calls = []

    monkeypatch.setattr(
        "app.worker.send_notification_in_worker",
        lambda db, *, notification_id: calls.append(notification_id),
    )

    job = Job(
        id="job-id",
        type=SEND_NOTIFICATION_JOB,
        payload={"notification_id": intent.id},
        attempts=0,
    )

    handle_job(job)

    assert calls == [intent.id]
