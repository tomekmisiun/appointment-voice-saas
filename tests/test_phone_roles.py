"""Tests for phone number role separation (P4-001).

Verifies that the three phone roles are independent and correctly wired:
  - business.phone         → inbound Twilio number; webhook routes by To=
  - owner_notification_phone → SMS alerts to the business owner
  - transfer_phone_number   → IVR call-transfer destination

Also verifies seed correctness, no legacy placeholder in any flow,
and that demo users cannot mutate business config.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from app.models.business import Business, TransferDestinationPolicy
from app.models.notification_outbox import NotificationOutbox
from app.models.tenant import Tenant
from app.seed_demo_data import (
    DEMO_BUSINESS_NAME,
    DEMO_INBOUND_PHONE,
    DEMO_OWNER_NOTIFICATION_PHONE,
    DEMO_TRANSFER_PHONE,
    DEMO_USER_EMAIL,
    seed_demo,
)
from app.services.business_service import (
    create_business,
    get_business_by_inbound_phone,
    update_business,
)
from app.services.customer_service import get_or_create_customer
from app.services.ivr_service import handle_keypress, start_session
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user

_STARTS_AT = datetime(2028, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_tenant(db):
    return db.query(Tenant).filter(Tenant.slug == "default").one()


def _make_demo_user(db, tenant_id: int):
    from app.core.security import hash_password
    import secrets
    from app.models.user import User

    existing = db.query(User).filter(
        User.email == DEMO_USER_EMAIL, User.tenant_id == tenant_id
    ).first()
    if existing is not None:
        return existing
    user = User(
        tenant_id=tenant_id,
        email=DEMO_USER_EMAIL,
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        is_active=True,
        role="user",
        is_demo_user=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _demo_headers(client, db, tenant_id: int, biz_id: int) -> dict:
    _make_demo_user(db, tenant_id)
    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = DEMO_USER_EMAIL
        ms.public_demo_business_id = biz_id
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_notification_domain(db, *, owner_notification_phone=None):
    """Create a minimal business+staff+service+customer for notification tests."""
    tenant = _default_tenant(db)
    biz = create_business(
        db,
        tenant_id=tenant.id,
        name="Notify Salon PR",
        timezone="Europe/Warsaw",
        phone=DEMO_INBOUND_PHONE,
        owner_notification_phone=owner_notification_phone,
    )
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30
    )
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48600900800"
    )
    return tenant.id, biz, staff.id, svc, customer


# ---------------------------------------------------------------------------
# get_business_by_inbound_phone
# ---------------------------------------------------------------------------

def test_get_business_by_inbound_phone_returns_matching_business(db):
    tenant = _default_tenant(db)
    create_business(
        db, tenant_id=tenant.id, name="Phone Lookup Salon", timezone="UTC",
        phone="+18174057514",
    )
    found = get_business_by_inbound_phone(db, "+18174057514")
    assert found is not None
    assert found.name == "Phone Lookup Salon"


def test_get_business_by_inbound_phone_returns_none_for_unknown(db):
    assert get_business_by_inbound_phone(db, "+19999999999") is None


def test_get_business_by_inbound_phone_returns_none_for_empty_string(db):
    assert get_business_by_inbound_phone(db, "") is None


def test_get_business_by_inbound_phone_returns_none_for_inactive(db):
    tenant = _default_tenant(db)
    biz = create_business(
        db, tenant_id=tenant.id, name="Inactive Phone Salon", timezone="UTC",
        phone="+18170000001",
    )
    update_business(db, biz.id, tenant.id, is_active=False)
    assert get_business_by_inbound_phone(db, "+18170000001") is None


# ---------------------------------------------------------------------------
# Webhook routing — To= field determines business
# ---------------------------------------------------------------------------

def test_inbound_webhook_routes_by_to_field(client, db):
    tenant = _default_tenant(db)
    create_business(
        db, tenant_id=tenant.id, name="Webhook Route Salon", timezone="UTC",
        phone="+18174000001",
    )
    resp = client.post(
        "/api/v1/webhooks/twilio/voice",
        data={"CallSid": "CA_route_001", "From": "+48600000001", "To": "+18174000001"},
    )
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "<Gather" in resp.text


def test_inbound_webhook_unknown_to_returns_hangup_twiml(client):
    resp = client.post(
        "/api/v1/webhooks/twilio/voice",
        data={"CallSid": "CA_route_002", "From": "+48600000002", "To": "+10000000000"},
    )
    assert resp.status_code == 200
    assert "<Hangup/>" in resp.text


# ---------------------------------------------------------------------------
# Notification service — phone role separation
# ---------------------------------------------------------------------------

def test_confirmation_customer_sms_uses_customer_phone(db):
    from app.services.booking_service import create_booking

    tenant_id, biz, staff_id, svc, customer = _make_notification_domain(
        db, owner_notification_phone="+48505460409"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id,
        customer_id=customer.id, service_id=svc.id, staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    outbox = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.booking_id == booking.id)
        .all()
    )
    recipients = {n.recipient_phone for n in outbox}
    assert customer.phone in recipients


def test_confirmation_owner_sms_uses_owner_notification_phone(db):
    from app.services.booking_service import create_booking

    tenant_id, biz, staff_id, svc, customer = _make_notification_domain(
        db, owner_notification_phone="+48505460409"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id,
        customer_id=customer.id, service_id=svc.id, staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    outbox = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.booking_id == booking.id)
        .all()
    )
    recipients = {n.recipient_phone for n in outbox}
    assert "+48505460409" in recipients


def test_confirmation_no_owner_sms_when_owner_notification_phone_unset(db):
    from app.services.booking_service import create_booking

    tenant_id, biz, staff_id, svc, customer = _make_notification_domain(
        db, owner_notification_phone=None
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id,
        customer_id=customer.id, service_id=svc.id, staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    outbox = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.booking_id == booking.id)
        .all()
    )
    assert len(outbox) == 1
    assert outbox[0].recipient_phone == customer.phone


def test_cancellation_owner_sms_uses_owner_notification_phone(db):
    from app.services.booking_service import cancel_booking, create_booking

    tenant_id, biz, staff_id, svc, customer = _make_notification_domain(
        db, owner_notification_phone="+48505460409"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id,
        customer_id=customer.id, service_id=svc.id, staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    cancel_booking(db, booking.id, biz.id, tenant_id)

    from app.models.notification_outbox import NotificationPurpose
    cancel_outbox = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking.id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_CANCELLATION,
        )
        .all()
    )
    recipients = {n.recipient_phone for n in cancel_outbox}
    assert "+48505460409" in recipients


def test_inbound_voice_number_is_not_used_as_owner_notification_recipient(db):
    from app.services.booking_service import create_booking

    tenant_id, biz, staff_id, svc, customer = _make_notification_domain(
        db, owner_notification_phone=None
    )
    create_booking(
        db, tenant_id=tenant_id, business_id=biz.id,
        customer_id=customer.id, service_id=svc.id, staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    outbox = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.business_id == biz.id)
        .all()
    )
    bad_recipients = [n for n in outbox if n.recipient_phone == biz.phone]
    assert bad_recipients == [], (
        f"Inbound Voice number {biz.phone} found in notification outbox"
    )


# ---------------------------------------------------------------------------
# IVR transfer — uses transfer_phone_number, not business.phone
# ---------------------------------------------------------------------------

def test_ivr_transfer_uses_transfer_phone_number(db):
    tenant = _default_tenant(db)
    biz = create_business(
        db, tenant_id=tenant.id, name="Transfer Role Salon", timezone="UTC",
        phone="+18174000002",
        transfer_phone_number="+48505460409",
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
    )
    session, _ = start_session(
        db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48600000009"
    )
    from app.core.ivr import IvrAction
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="2")
    assert resp.action == IvrAction.TRANSFER
    assert resp.transfer_destination == "+48505460409"


def test_ivr_transfer_does_not_use_inbound_phone(db):
    """business.phone (inbound routing number) must not serve as transfer destination."""
    tenant = _default_tenant(db)
    biz = create_business(
        db, tenant_id=tenant.id, name="No Transfer Mix Salon", timezone="UTC",
        phone="+18174000003",
        # transfer_phone_number intentionally omitted
        transfer_enabled=True,
        transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
    )
    session, _ = start_session(
        db, business_id=biz.id, tenant_id=tenant.id, caller_phone="+48600000010"
    )
    from app.core.ivr import IvrAction
    resp = handle_keypress(db, session_id=session.id, tenant_id=tenant.id, key="2")
    # Without transfer_phone_number the IVR must fall back to CONTINUE, not
    # accidentally transfer to the inbound Twilio number.
    assert resp.action == IvrAction.CONTINUE
    assert resp.transfer_destination is None


# ---------------------------------------------------------------------------
# Seed — phone fields
# ---------------------------------------------------------------------------

def test_seed_sets_correct_inbound_phone(db):
    seed_demo(db)
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()
    assert biz.phone == DEMO_INBOUND_PHONE


def test_seed_uses_configured_voice_number_without_changing_owner_phone(db):
    with patch("app.seed_demo_data.settings") as ms:
        ms.twilio_voice_number = "+18174057514"
        ms.public_demo_business_id = 0
        ms.public_demo_user_email = DEMO_USER_EMAIL
        seed_demo(db)

    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()
    assert biz.phone == "+18174057514"
    assert biz.owner_notification_phone == DEMO_OWNER_NOTIFICATION_PHONE


def test_seed_sets_correct_owner_notification_phone(db):
    seed_demo(db)
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()
    assert biz.owner_notification_phone == DEMO_OWNER_NOTIFICATION_PHONE


def test_seed_sets_correct_transfer_phone(db):
    seed_demo(db)
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()
    assert biz.transfer_phone_number == DEMO_TRANSFER_PHONE


def test_seed_update_is_idempotent_no_duplicate_business(db):
    seed_demo(db)
    seed_demo(db)
    count = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).count()
    assert count == 1


def test_seed_rerun_updates_phone_fields(db):
    """A second seed run must update phone fields, not silently skip them."""
    seed_demo(db)
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()
    # Corrupt the fields to simulate stale DB state.
    biz.phone = "+10000000000"
    biz.owner_notification_phone = None
    biz.transfer_phone_number = None
    db.commit()

    seed_demo(db)
    db.refresh(biz)
    assert biz.phone == DEMO_INBOUND_PHONE
    assert biz.owner_notification_phone == DEMO_OWNER_NOTIFICATION_PHONE
    assert biz.transfer_phone_number == DEMO_TRANSFER_PHONE


def test_seed_updates_configured_public_demo_business_id(db):
    tenant = _default_tenant(db)
    stale_demo = create_business(
        db,
        tenant_id=tenant.id,
        name=DEMO_BUSINESS_NAME,
        timezone="Europe/Warsaw",
        phone="+48100200300",
        owner_notification_phone=None,
        transfer_phone_number=None,
    )

    with patch("app.seed_demo_data.settings") as ms:
        ms.public_demo_business_id = stale_demo.id
        ms.twilio_voice_number = ""
        ms.public_demo_user_email = DEMO_USER_EMAIL
        seed_demo(db)

    db.refresh(stale_demo)
    assert stale_demo.phone == DEMO_INBOUND_PHONE
    assert stale_demo.owner_notification_phone == DEMO_OWNER_NOTIFICATION_PHONE
    assert stale_demo.transfer_phone_number == DEMO_TRANSFER_PHONE


# ---------------------------------------------------------------------------
# Demo user read-only — cannot mutate business phone config
# ---------------------------------------------------------------------------

def test_demo_user_cannot_patch_business(client, db):
    register_user(client, "pr_owner@example.com")
    promote_to_admin(db, "pr_owner@example.com")
    token = login_user(client, "pr_owner@example.com").json()["access_token"]
    owner_headers = auth_headers(token)

    resp = client.post(
        "/api/v1/businesses",
        json={"name": "PR Demo Biz", "timezone": "UTC"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    biz_id = resp.json()["id"]

    tenant_id = _default_tenant(db).id
    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"phone": "+10000000001"},
        headers=demo_hdrs,
    )
    assert resp.status_code == 403
