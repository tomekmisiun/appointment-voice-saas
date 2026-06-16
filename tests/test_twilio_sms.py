"""Tests for Twilio SMS provider (AVS-H003) and SMS status webhook (AVS-H004)."""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.notification_outbox import NotificationOutbox, NotificationStatus
from app.models.tenant import Tenant
from app.services.business_service import create_business
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
        provider = TwilioSmsProvider("AC123", "token", "+48800000001")
        result = provider.send(SmsMessage(to="+48600000001", body="Hello"))

    assert result.success is True
    assert result.provider_message_id == "SM_test_123"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["auth"] == ("AC123", "token")
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
        provider = TwilioSmsProvider("AC123", "token", "+48800000001")
        result = provider.send(SmsMessage(to="invalid", body="Hello"))

    assert result.success is False
    assert "400" in result.error


def test_twilio_sms_provider_request_error():
    import httpx
    from app.services.sms_provider import TwilioSmsProvider
    from app.core.sms import SmsMessage

    with patch("httpx.post", side_effect=httpx.ConnectError("timeout")):
        provider = TwilioSmsProvider("AC123", "token", "+48800000001")
        result = provider.send(SmsMessage(to="+48600000001", body="Hello"))

    assert result.success is False
    assert result.error == "twilio_request_error"


def test_get_sms_provider_returns_twilio_when_configured():
    from app.services.sms_provider import TwilioSmsProvider, get_sms_provider

    mock_settings = MagicMock()
    mock_settings.twilio_account_sid = "AC123"
    mock_settings.twilio_auth_token = "token"
    mock_settings.twilio_from_number = "+48800000001"

    with patch("app.services.sms_provider.settings", mock_settings):
        provider = get_sms_provider()

    assert isinstance(provider, TwilioSmsProvider)


def test_get_sms_provider_returns_null_when_unconfigured():
    from app.services.sms_provider import NullSmsProvider, get_sms_provider

    mock_settings = MagicMock()
    mock_settings.twilio_account_sid = ""
    mock_settings.twilio_auth_token = ""
    mock_settings.twilio_from_number = ""

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
