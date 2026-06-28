"""Tests for Twilio SMS provider (AVS-H003) and SMS status webhook (AVS-H004)."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.booking import BookingStatus
from app.models.notification_outbox import NotificationOutbox, NotificationStatus
from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from tests.database import promote_to_admin, register_user


# ---------------------------------------------------------------------------
# TwilioSmsProvider unit tests
# ---------------------------------------------------------------------------

def test_twilio_sms_provider_success():
    from app.services.sms_provider import TwilioSmsProvider
    from app.core.sms import SmsMessage

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"sid": "SM_test_123"}
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        provider = TwilioSmsProvider("AC123", "token", "VoxSlot")
        result = provider.send(SmsMessage(to="+48600000001", body="Hello"))

    assert result.success is True
    assert result.provider_message_id == "SM_test_123"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["auth"] == ("AC123", "token")
    assert call_kwargs.kwargs["data"]["From"] == "VoxSlot"
    assert call_kwargs.kwargs["data"]["To"] == "+48600000001"


def test_twilio_sms_provider_http_error():
    import httpx
    from app.services.sms_provider import TwilioSmsProvider
    from app.core.sms import SmsMessage

    error_resp = MagicMock()
    error_resp.status_code = 400
    error_resp.text = "Invalid number"
    exc = httpx.HTTPStatusError("bad", request=MagicMock(), response=error_resp)

    with patch("httpx.post", side_effect=exc):
        provider = TwilioSmsProvider("AC123", "token", "VoxSlot")
        result = provider.send(SmsMessage(to="invalid", body="Hello"))

    assert result.success is False
    assert "400" in result.error


def test_twilio_sms_provider_request_error():
    import httpx
    from app.services.sms_provider import TwilioSmsProvider
    from app.core.sms import SmsMessage

    with patch("httpx.post", side_effect=httpx.ConnectError("timeout")):
        provider = TwilioSmsProvider("AC123", "token", "VoxSlot")
        result = provider.send(SmsMessage(to="+48600000001", body="Hello"))

    assert result.success is False
    assert result.error == "twilio_request_error"


def test_get_sms_provider_returns_twilio_when_configured():
    from app.services.sms_provider import TwilioSmsProvider, get_sms_provider

    mock_settings = MagicMock()
    mock_settings.twilio_account_sid = "AC123"
    mock_settings.twilio_auth_token = "token"
    mock_settings.twilio_sms_from = "VoxSlot"

    with patch("app.services.sms_provider.settings", mock_settings):
        provider = get_sms_provider()

    assert isinstance(provider, TwilioSmsProvider)


def test_get_sms_provider_returns_null_when_unconfigured():
    from app.services.sms_provider import NullSmsProvider, get_sms_provider

    mock_settings = MagicMock()
    mock_settings.twilio_account_sid = ""
    mock_settings.twilio_auth_token = ""
    mock_settings.twilio_sms_from = ""

    with patch("app.services.sms_provider.settings", mock_settings):
        provider = get_sms_provider()

    assert isinstance(provider, NullSmsProvider)


# ---------------------------------------------------------------------------
# SMS status webhook integration tests (AVS-H004/H005)
# ---------------------------------------------------------------------------

@pytest.fixture()
def sms_domain(db, client):
    register_user(client, "sms_admin@example.com")
    promote_to_admin(db, "sms_admin@example.com")

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="SMS Test Salon", timezone="UTC")

    unique_sid = f"SM_{uuid.uuid4().hex[:16]}"
    notif = NotificationOutbox(
        tenant_id=tenant.id,
        business_id=biz.id,
        channel="sms",
        purpose="booking_confirmation",
        recipient_phone="+48600000099",
        body="Test notification",
        status=NotificationStatus.SENT,
        provider_message_id=unique_sid,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return {"client": client, "notification": notif, "db": db, "sid": unique_sid}


def test_sms_status_delivered_no_change(sms_domain, db):
    client, notif, sid = sms_domain["client"], sms_domain["notification"], sms_domain["sid"]

    resp = client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": sid, "MessageStatus": "delivered"},
    )
    assert resp.status_code == 204
    db.refresh(notif)
    assert notif.status == NotificationStatus.SENT


def test_sms_status_failed_marks_notification_failed(sms_domain, db):
    client, notif, sid = sms_domain["client"], sms_domain["notification"], sms_domain["sid"]

    resp = client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": sid, "MessageStatus": "failed"},
    )
    assert resp.status_code == 204
    db.refresh(notif)
    assert notif.status == NotificationStatus.FAILED
    assert "failed" in notif.last_error


def test_sms_status_undelivered_marks_notification_failed(sms_domain, db):
    client, notif, sid = sms_domain["client"], sms_domain["notification"], sms_domain["sid"]

    resp = client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": sid, "MessageStatus": "undelivered"},
    )
    assert resp.status_code == 204
    db.refresh(notif)
    assert notif.status == NotificationStatus.FAILED


def test_sms_status_unknown_sid_ignored(sms_domain):
    client = sms_domain["client"]

    resp = client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": "SM_unknown_99999", "MessageStatus": "failed"},
    )
    assert resp.status_code == 204


def test_sms_status_idempotent(sms_domain, db):
    client, notif, sid = sms_domain["client"], sms_domain["notification"], sms_domain["sid"]

    client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": sid, "MessageStatus": "failed"},
    )
    resp2 = client.post(
        "/api/v1/webhooks/twilio/sms/status",
        data={"SmsSid": sid, "MessageStatus": "failed"},
    )
    assert resp2.status_code == 204
    db.refresh(notif)
    assert notif.status == NotificationStatus.FAILED


# ---------------------------------------------------------------------------
# SMS inbound reply webhook (P1-002)
# ---------------------------------------------------------------------------

@pytest.fixture()
def sms_reply_domain(db, client):
    register_user(client, "sms_reply_admin@example.com")
    promote_to_admin(db, "sms_reply_admin@example.com")

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reply Webhook Salon", timezone="UTC")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48811100000"
    )
    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(hours=3),
    )
    return {"client": client, "business": biz, "customer": customer, "booking": booking}


def test_sms_inbound_cancel_cancels_booking(sms_reply_domain, db):
    client = sms_reply_domain["client"]
    biz = sms_reply_domain["business"]
    customer = sms_reply_domain["customer"]
    booking = sms_reply_domain["booking"]

    resp = client.post(
        f"/api/v1/webhooks/twilio/sms/{biz.id}/inbound",
        data={"From": customer.phone, "Body": "X"},
    )

    assert resp.status_code == 204
    db.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


def test_sms_inbound_confirm_leaves_booking_confirmed(sms_reply_domain, db):
    client = sms_reply_domain["client"]
    biz = sms_reply_domain["business"]
    customer = sms_reply_domain["customer"]
    booking = sms_reply_domain["booking"]

    resp = client.post(
        f"/api/v1/webhooks/twilio/sms/{biz.id}/inbound",
        data={"From": customer.phone, "Body": "C"},
    )

    assert resp.status_code == 204
    db.refresh(booking)
    assert booking.status == BookingStatus.CONFIRMED


def test_sms_inbound_unknown_business_returns_no_content(db, client):
    resp = client.post(
        "/api/v1/webhooks/twilio/sms/999999/inbound",
        data={"From": "+48800000000", "Body": "X"},
    )
    assert resp.status_code == 204
