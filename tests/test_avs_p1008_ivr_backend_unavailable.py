"""P1-008: IVR backend-unavailable fallback.

If the DB or Redis is unavailable mid-call, the voice webhook must not leak
a raw 500/JSON error to Twilio (which expects TwiML) or crash the call. It
must return graceful TwiML telling the caller to call back later, with no
partial VoiceSession/booking state left behind.
"""
from sqlalchemy.exc import OperationalError

from app.models.tenant import Tenant
from app.models.voice_session import VoiceSession
from app.services.business_service import create_business
from tests.database import promote_to_admin, register_user


def _db_unavailable(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("connection refused"))


class _UnavailableRedis:
    def incr(self, *args, **kwargs):
        from redis.exceptions import ConnectionError as RedisConnectionError
        raise RedisConnectionError("redis unavailable")

    def expire(self, *args, **kwargs):
        from redis.exceptions import ConnectionError as RedisConnectionError
        raise RedisConnectionError("redis unavailable")


def _setup(db, client):
    register_user(client, "p1008_admin@example.com")
    promote_to_admin(db, "p1008_admin@example.com")
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Outage Salon", timezone="UTC")
    return biz.id


def test_inbound_call_db_unavailable_returns_graceful_twiml(db, client, monkeypatch):
    biz_id = _setup(db, client)
    monkeypatch.setattr("app.api.routes.twilio_voice.get_business_global", _db_unavailable)

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_001", "From": "+48600000010", "To": "+48800000000"},
    )

    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "technical difficulties" in resp.text.lower()
    assert "<Hangup/>" in resp.text
    assert db.query(VoiceSession).filter(VoiceSession.call_sid == "CA_outage_001").first() is None


def test_inbound_call_redis_unavailable_returns_graceful_twiml(db, client, monkeypatch):
    biz_id = _setup(db, client)
    monkeypatch.setattr("app.api.dependencies.rate_limit.redis_client", _UnavailableRedis())

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_002", "From": "+48600000011", "To": "+48800000000"},
    )

    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "technical difficulties" in resp.text.lower()
    assert "<Hangup/>" in resp.text


def test_keypress_db_unavailable_returns_graceful_twiml(db, client, monkeypatch):
    biz_id = _setup(db, client)
    client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_003", "From": "+48600000012", "To": "+48800000000"},
    )
    session = db.query(VoiceSession).filter(VoiceSession.call_sid == "CA_outage_003").one()

    monkeypatch.setattr("app.api.routes.twilio_voice.get_business_global", _db_unavailable)

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}/{session.id}",
        data={"CallSid": "CA_outage_003", "Digits": "1"},
    )

    assert resp.status_code == 200
    assert "technical difficulties" in resp.text.lower()
    assert "<Hangup/>" in resp.text


def test_keypress_redis_unavailable_returns_graceful_twiml(db, client, monkeypatch):
    biz_id = _setup(db, client)
    client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_004", "From": "+48600000013", "To": "+48800000000"},
    )
    session = db.query(VoiceSession).filter(VoiceSession.call_sid == "CA_outage_004").one()

    monkeypatch.setattr("app.api.dependencies.rate_limit.redis_client", _UnavailableRedis())

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}/{session.id}",
        data={"CallSid": "CA_outage_004", "Digits": "1"},
    )

    assert resp.status_code == 200
    assert "technical difficulties" in resp.text.lower()
    assert "<Hangup/>" in resp.text


def test_rate_limit_exceeded_is_not_treated_as_backend_unavailable(db, client, monkeypatch):
    """A real 429 (limit exceeded, Redis healthy) must stay a 429 — only a
    Redis-outage-flavored HTTPException(503) should become graceful TwiML."""
    biz_id = _setup(db, client)
    monkeypatch.setattr("app.core.config.settings.twilio_voice_rate_limit_limit", 1)

    client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_006", "From": "+48600000015", "To": "+48800000000"},
    )
    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_007", "From": "+48600000016", "To": "+48800000000"},
    )

    assert resp.status_code == 429


def test_signature_failure_is_not_treated_as_backend_unavailable(db, client, monkeypatch):
    """A bad/missing Twilio signature must still 403 — the new except clause
    only catches OperationalError/RedisError, not HTTPException."""
    biz_id = _setup(db, client)
    monkeypatch.setattr("app.core.config.settings.twilio_auth_token", "some-secret")

    resp = client.post(
        f"/api/v1/webhooks/twilio/voice/{biz_id}",
        data={"CallSid": "CA_outage_005", "From": "+48600000014", "To": "+48800000000"},
    )

    assert resp.status_code == 403
