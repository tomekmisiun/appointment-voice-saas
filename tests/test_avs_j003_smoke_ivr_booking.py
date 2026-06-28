"""AVS-J003: Smoke — IVR simulated call-to-booking with fake SMS and fake calendar.

Proves the full voice path works locally using seeded demo data:
  simulate call → press 1 (book) → press 1 (service) → press 0 (any available
  staff) → press 1 (slot) → press 1 (confirm) → booking in DB, SMS enqueued.

The demo business seeds 3 staff members and only business-level working
hours (no staff-specific schedule). Since P3-002, staff with no
staff-specific override fall back to the business's hours, so all 3 are
"schedulable" (P2-006) and the staff-selection step is offered -- this
smoke test presses "0" (any available staff) to keep the overall flow
simple; dedicated staff-selection behavior is covered by
`tests/test_avs_p2006_ivr_staff_selection.py`.
"""
import pytest

from app.core.ivr import IvrAction
from app.models.booking import Booking, BookingSource
from app.models.notification_outbox import NotificationOutbox
from app.models.tenant import Tenant
from app.seed_demo_data import DEMO_BUSINESS_NAME, seed_demo
from tests.database import auth_headers, login_user, promote_to_admin, register_user


@pytest.fixture()
def ivr_smoke(db, client):
    seed_demo(db)
    from app.models.business import Business
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()

    register_user(client, "j003_admin@example.com")
    promote_to_admin(db, "j003_admin@example.com")
    token = login_user(client, "j003_admin@example.com").json()["access_token"]

    return {
        "db": db,
        "client": client,
        "headers": auth_headers(token),
        "tenant_id": tenant.id,
        "biz_id": biz.id,
    }


def _press(client, headers, session_id, key):
    return client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": key},
        headers=headers,
    )


def test_ivr_smoke_full_booking_flow(ivr_smoke):
    """Simulate a complete IVR call-to-booking using the demo business."""
    client, headers = ivr_smoke["client"], ivr_smoke["headers"]
    biz_id = ivr_smoke["biz_id"]
    db = ivr_smoke["db"]

    # Start call → main menu
    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900100200"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    session_id = data["session_id"]
    assert data["action"] == IvrAction.CONTINUE
    assert any(o["key"] == "1" for o in data["options"])

    # Press 1 (book) → service selection
    resp = _press(client, headers, session_id, "1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.CONTINUE
    assert len(data["options"]) >= 1

    # Press 1 (pick service) → staff selection
    resp = _press(client, headers, session_id, "1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.CONTINUE
    assert len(data["options"]) >= 1

    # Press 0 (any available staff) → slot selection
    resp = _press(client, headers, session_id, "0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.CONTINUE
    assert len(data["options"]) >= 1

    # Press 1 (pick slot) → booking confirmed
    resp = _press(client, headers, session_id, "1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.END

    # Booking must exist in DB with IVR source
    booking = db.query(Booking).filter(
        Booking.tenant_id == ivr_smoke["tenant_id"],
        Booking.source == BookingSource.IVR,
    ).first()
    assert booking is not None


def test_ivr_smoke_enqueues_sms_after_booking(ivr_smoke):
    client, headers = ivr_smoke["client"], ivr_smoke["headers"]
    biz_id = ivr_smoke["biz_id"]
    db = ivr_smoke["db"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900100201"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]

    _press(client, headers, session_id, "1")  # book
    _press(client, headers, session_id, "1")  # pick service
    _press(client, headers, session_id, "0")  # any available staff
    _press(client, headers, session_id, "1")  # pick slot -> booking confirmed

    outbox = db.query(NotificationOutbox).filter(
        NotificationOutbox.tenant_id == ivr_smoke["tenant_id"],
    ).all()
    assert len(outbox) >= 1


def test_ivr_smoke_transfer_path(ivr_smoke):
    """Press 2 on demo business (transfer_enabled=True) must return TRANSFER action."""
    client, headers = ivr_smoke["client"], ivr_smoke["headers"]
    biz_id = ivr_smoke["biz_id"]

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": "+48900100202"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]

    resp = _press(client, headers, session_id, "2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.TRANSFER
    assert data["transfer_destination"] == "+48505460409"
