"""AVS-K001: booking_mode and subscription_plan — schema, API, IVR, notifications.

Two independent dimensions:
  booking_mode      — operational: press-1 routes to internal flow or external link SMS
  subscription_plan — commercial: stored only, no enforcement today
"""
import pytest

from app.core.ivr import IvrAction
from app.models.business import BookingMode, SubscriptionPlan
from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.schemas.business import BusinessCreate
from app.services.business_service import create_business, get_business
from app.services.notification_service import enqueue_external_booking_link_sms
from app.services.plan_policy_service import PlanPolicy, get_plan_policy
from tests.database import auth_headers, login_user, promote_to_admin, register_user


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin(db, client):
    register_user(client, "k001_admin@example.com")
    promote_to_admin(db, "k001_admin@example.com")
    token = login_user(client, "k001_admin@example.com").json()["access_token"]
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    return {
        "client": client,
        "headers": auth_headers(token),
        "tenant_id": tenant.id,
        "db": db,
    }


def _press(client, headers, session_id, key):
    return client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": key},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_business_create_defaults_to_internal_booking():
    schema = BusinessCreate(name="Salon", timezone="UTC")
    assert schema.booking_mode == BookingMode.INTERNAL_BOOKING
    assert schema.subscription_plan == SubscriptionPlan.FULL_BOOKING
    assert schema.external_booking_url is None


def test_business_create_external_link_requires_url():
    with pytest.raises(ValueError, match="external_booking_url is required"):
        BusinessCreate(
            name="Salon",
            timezone="UTC",
            booking_mode=BookingMode.EXTERNAL_BOOKING_LINK,
        )


def test_business_create_external_link_with_url_passes():
    schema = BusinessCreate(
        name="Salon",
        timezone="UTC",
        booking_mode=BookingMode.EXTERNAL_BOOKING_LINK,
        external_booking_url="https://booksy.com/en-us/123",
        external_booking_label="Book on Booksy",
    )
    assert schema.booking_mode == BookingMode.EXTERNAL_BOOKING_LINK
    assert schema.external_booking_url == "https://booksy.com/en-us/123"


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------

def test_model_defaults_booking_mode(db, admin):
    biz = create_business(db, tenant_id=admin["tenant_id"], name="Default Biz", timezone="UTC")
    assert biz.booking_mode == BookingMode.INTERNAL_BOOKING
    assert biz.subscription_plan == SubscriptionPlan.FULL_BOOKING
    assert biz.external_booking_url is None
    assert biz.external_booking_label is None
    assert biz.external_booking_provider is None


# ---------------------------------------------------------------------------
# API: POST creates business with new fields
# ---------------------------------------------------------------------------

def test_api_create_business_defaults_returned(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={"name": "API Default Salon", "timezone": "UTC"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["booking_mode"] == "internal_booking"
    assert data["subscription_plan"] == "full_booking"
    assert data["external_booking_url"] is None


def test_api_create_business_external_mode(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Booksy Salon",
            "timezone": "UTC",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/123",
            "external_booking_label": "Book on Booksy",
            "subscription_plan": "booksy_lite",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["booking_mode"] == "external_booking_link"
    assert data["external_booking_url"] == "https://booksy.com/123"
    assert data["external_booking_label"] == "Book on Booksy"
    assert data["subscription_plan"] == "booksy_lite"


def test_api_create_business_external_mode_without_url_rejected(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Missing URL Salon",
            "timezone": "UTC",
            "booking_mode": "external_booking_link",
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API: PATCH can change booking_mode and subscription_plan
# ---------------------------------------------------------------------------

def test_api_patch_booking_mode(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Patch Mode Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/456",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["booking_mode"] == "external_booking_link"
    assert resp.json()["external_booking_url"] == "https://booksy.com/456"


def test_api_patch_subscription_plan(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Plan Switch Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"subscription_plan": "booksy_pro"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["subscription_plan"] == "booksy_pro"


# ---------------------------------------------------------------------------
# IVR: main menu prompt is mode-aware
# ---------------------------------------------------------------------------

def test_ivr_main_menu_internal_booking_mode(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Internal IVR Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900000001"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "book an appointment" in data["prompt"].lower()
    assert any(o["key"] == "1" for o in data["options"])


def test_ivr_main_menu_external_booking_mode(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={
            "name": "External IVR Salon",
            "timezone": "UTC",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/789",
        },
        headers=headers,
    ).json()["id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900000002"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "link" in data["prompt"].lower()
    assert any(o["key"] == "1" for o in data["options"])


# ---------------------------------------------------------------------------
# IVR: press 1 dispatches on booking_mode
# ---------------------------------------------------------------------------

def test_ivr_press1_internal_booking_enters_service_selection(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Press1 Internal Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900000003"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]

    resp = _press(client, headers, session_id, "1")
    assert resp.status_code == 200
    # No services configured → NO_SLOTS terminal OR service selection; either way not an error
    data = resp.json()
    assert data["action"] in (IvrAction.CONTINUE, IvrAction.END)


def test_ivr_press1_external_booking_sends_link_and_ends(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={
            "name": "Press1 External Salon",
            "timezone": "UTC",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/abc",
            "external_booking_label": "Book now",
        },
        headers=headers,
    ).json()["id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900000004"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]

    resp = _press(client, headers, session_id, "1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.END
    assert "sms" in data["prompt"].lower() or "link" in data["prompt"].lower()


def test_ivr_external_link_session_is_terminal(admin):
    """After EXTERNAL_LINK_SENT, further keypresses return END."""
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={
            "name": "Terminal External Salon",
            "timezone": "UTC",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/def",
        },
        headers=headers,
    ).json()["id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900000005"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]
    _press(client, headers, session_id, "1")  # → EXTERNAL_LINK_SENT

    resp = _press(client, headers, session_id, "1")  # second press → terminal
    assert resp.status_code == 200
    assert resp.json()["action"] == IvrAction.END


# ---------------------------------------------------------------------------
# Notification: external booking link SMS
# ---------------------------------------------------------------------------

def test_enqueue_external_booking_link_sms_creates_outbox(db, admin):
    biz = create_business(
        db,
        tenant_id=admin["tenant_id"],
        name="Link SMS Biz",
        timezone="UTC",
        booking_mode="external_booking_link",
        external_booking_url="https://booksy.com/ghi",
    )

    intent = enqueue_external_booking_link_sms(
        db,
        business=biz,
        caller_phone="+48900000010",
        url="https://booksy.com/ghi",
        label="Book on Booksy",
    )
    db.commit()

    outbox = db.query(NotificationOutbox).filter(
        NotificationOutbox.id == intent.id
    ).one()
    assert outbox.purpose == NotificationPurpose.EXTERNAL_BOOKING_LINK
    assert outbox.booking_id is None
    assert outbox.recipient_phone == "+48900000010"
    assert "https://booksy.com/ghi" in outbox.body
    assert outbox.tenant_id == biz.tenant_id
    assert outbox.business_id == biz.id


def test_enqueue_external_booking_link_sms_default_label(db, admin):
    biz = create_business(
        db,
        tenant_id=admin["tenant_id"],
        name="Default Label Biz",
        timezone="UTC",
    )
    intent = enqueue_external_booking_link_sms(
        db,
        business=biz,
        caller_phone="+48900000011",
        url="https://example.com/book",
        label=None,
    )
    db.commit()
    outbox = db.query(NotificationOutbox).filter(NotificationOutbox.id == intent.id).one()
    assert "Book online" in outbox.body


# ---------------------------------------------------------------------------
# PlanPolicyService stub
# ---------------------------------------------------------------------------

def test_get_plan_policy_returns_permissive_policy(db, admin):
    biz = create_business(
        db,
        tenant_id=admin["tenant_id"],
        name="Policy Biz",
        timezone="UTC",
        subscription_plan="booksy_lite",
    )
    policy = get_plan_policy(biz)
    assert isinstance(policy, PlanPolicy)
    assert policy.live_transfer_enabled is True
    assert policy.callback_enabled is True
    assert policy.sms_limit is None
    assert policy.ivr_minutes_limit is None


def test_get_plan_policy_same_for_all_plans(db, admin):
    for plan in ("booksy_lite", "booksy_pro", "full_booking", "full_booking_pro"):
        biz = create_business(
            db,
            tenant_id=admin["tenant_id"],
            name=f"Plan Biz {plan}",
            timezone="UTC",
            subscription_plan=plan,
        )
        policy = get_plan_policy(biz)
        assert policy.live_transfer_enabled is True, f"failed for plan={plan}"
