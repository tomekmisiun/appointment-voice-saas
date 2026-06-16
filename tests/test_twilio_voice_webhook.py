"""Tests for Twilio voice webhook adapter (AVS-H001/H002/H005/H006)."""
import base64
import hashlib
import hmac

import pytest

from app.models.tenant import Tenant
from app.models.voice_session import VoiceSession
from app.services.business_service import create_business
from tests.database import login_user, promote_to_admin, register_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _twilio_sig(auth_token: str, url: str, params: dict[str, str]) -> str:
    s = url + "".join(k + params[k] for k in sorted(params))
    mac = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


@pytest.fixture()
def domain(db, client):
    register_user(client, "twilio_admin@example.com")
    promote_to_admin(db, "twilio_admin@example.com")
    token = login_user(client, "twilio_admin@example.com").json()["access_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Voice Test Salon", timezone="UTC")
    return {"client": client, "token": token, "business_id": biz.id, "tenant_id": tenant.id}


# ---------------------------------------------------------------------------
# TwiML adapter unit tests
# ---------------------------------------------------------------------------

def test_twiml_continue_includes_gather():
    from app.core.ivr import IvrAction, IvrOption, IvrResponse
    from app.services.twilio_voice_adapter import ivr_to_twiml

    resp = IvrResponse(
        prompt="Press 1 to book.",
        options=(IvrOption(key="1", label="Book"),),
        action=IvrAction.CONTINUE,
    )
    xml = ivr_to_twiml(resp, gather_action_url="https://example.com/api/v1/webhooks/twilio/voice/1/42")
    assert "<Gather" in xml
    assert 'action="https://example.com/api/v1/webhooks/twilio/voice/1/42"' in xml
    assert "Press 1 to book." in xml


def test_twiml_end_includes_hangup():
    from app.core.ivr import IvrAction, IvrResponse
    from app.services.twilio_voice_adapter import ivr_to_twiml

    resp = IvrResponse(prompt="Goodbye.", action=IvrAction.END)
    xml = ivr_to_twiml(resp)
    assert "<Hangup/>" in xml
    assert "<Gather" not in xml


def test_twiml_transfer_includes_dial():
    from app.core.ivr import IvrAction, IvrResponse
    from app.services.twilio_voice_adapter import ivr_to_twiml

    resp = IvrResponse(prompt="Transferring.", action=IvrAction.TRANSFER)
    xml = ivr_to_twiml(resp, transfer_to="+48123456789")
    assert "<Dial>+48123456789</Dial>" in xml


def test_twiml_transfer_without_number_hangs_up():
    from app.core.ivr import IvrAction, IvrResponse
    from app.services.twilio_voice_adapter import ivr_to_twiml

    resp = IvrResponse(prompt="Transferring.", action=IvrAction.TRANSFER)
    xml = ivr_to_twiml(resp)
    assert "<Hangup/>" in xml
    assert "<Dial>" not in xml


def test_twiml_escapes_prompt():
    from app.core.ivr import IvrAction, IvrResponse
    from app.services.twilio_voice_adapter import ivr_to_twiml

    resp = IvrResponse(prompt="<script>alert(1)</script>", action=IvrAction.END)
    xml = ivr_to_twiml(resp)
    assert "<script>" not in xml
    assert "&lt;script&gt;" in xml


# ---------------------------------------------------------------------------
# Signature verification unit tests
# ---------------------------------------------------------------------------

def test_twilio_signature_valid():
    from app.core.twilio_security import verify_twilio_signature

    token = "secret123"
    url = "https://example.com/api/v1/webhooks/twilio/voice/1"
    params = {"CallSid": "CA123", "From": "+48600000001"}
    sig = _twilio_sig(token, url, params)
    verify_twilio_signature(url=url, form_data=params, signature=sig, auth_token=token)


def test_twilio_signature_invalid():
    from app.core.twilio_security import TwilioSignatureError, verify_twilio_signature

    with pytest.raises(TwilioSignatureError):
        verify_twilio_signature(
            url="https://example.com/api/v1/webhooks/twilio/voice/1",
            form_data={"CallSid": "CA123"},
            signature="bad",
            auth_token="secret",
        )


def test_twilio_signature_skipped_when_no_auth_token():
    from app.core.twilio_security import verify_twilio_signature

    verify_twilio_signature(url="https://x.com", form_data={}, signature="anything", auth_token="")


# ---------------------------------------------------------------------------
# Voice webhook integration tests (no real Twilio auth configured)
# ---------------------------------------------------------------------------

def test_inbound_call_creates_session(domain):
    client, biz_id = domain["client"], domain["business_id"]

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_test_001", "From": "+48600000002", "To": "+48800000000"},
    )
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "<Gather" in resp.text
    assert "Press 1 to book" in resp.text


def test_inbound_call_returns_twiml_for_unknown_business(domain):
    client = domain["client"]

    resp = client.post(
        "/api/v1/webhooks/twilio/voice/99999",
        data={"CallSid": "CA_test_002", "From": "+48600000003", "To": "+48800000000"},
    )
    assert resp.status_code == 200
    assert "<Hangup/>" in resp.text


def test_inbound_call_idempotent_on_retry(domain, db):
    client, biz_id = domain["client"], domain["business_id"]

    data = {"CallSid": "CA_idempotent", "From": "+48600000004", "To": "+48800000000"}
    resp1 = client.post(f"/api/v1/webhooks/twilio/voice/{biz_id}", data=data)
    resp2 = client.post(f"/api/v1/webhooks/twilio/voice/{biz_id}", data=data)

    sessions = db.query(VoiceSession).filter(VoiceSession.call_sid == "CA_idempotent").all()
    assert len(sessions) == 1
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_keypress_returns_service_menu(domain, db):
    client, biz_id = domain["client"], domain["business_id"]

    client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_press_001", "From": "+48600000005", "To": "+48800000000"},
    )
    session = db.query(VoiceSession).filter(VoiceSession.call_sid == "CA_press_001").one()

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}/{session.id}",
        data={"CallSid": "CA_press_001", "Digits": "1"},
    )
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]


def test_keypress_invalid_session_returns_twiml(domain):
    client, biz_id = domain["client"], domain["business_id"]

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}/99999",
        data={"CallSid": "CA_bad", "Digits": "1"},
    )
    assert resp.status_code == 200
    assert "<Hangup/>" in resp.text
