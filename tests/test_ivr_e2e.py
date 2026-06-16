"""E2E IVR simulation test (AVS-G010).

Full flow: simulated call → service selection → slot selection → booking created
           with fake SMS and fake calendar side-effects.
"""

from datetime import time

import pytest

from app.core.ivr import IvrAction
from app.models.booking import Booking, BookingSource
from app.models.notification_outbox import NotificationOutbox
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.service_service import create_service
from app.services.working_hours_service import create_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user


@pytest.fixture()
def ivr_domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="E2E Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30
    )
    for day in range(7):
        create_working_hours(
            db,
            tenant_id=tenant.id,
            business_id=biz.id,
            staff_id=None,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
    return {"tenant_id": tenant.id, "business_id": biz.id, "service_id": svc.id}


@pytest.fixture()
def admin_client(client, db):
    register_user(client, "ivr_admin@example.com")
    promote_to_admin(db, "ivr_admin@example.com")
    token = login_user(client, "ivr_admin@example.com").json()["access_token"]
    return client, auth_headers(token)


def test_e2e_ivr_full_booking_flow(db, admin_client, ivr_domain):
    client, headers = admin_client
    biz_id = ivr_domain["business_id"]
    caller = "+48600999001"

    # Step 1: Start call → main menu
    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": biz_id, "caller_phone": caller},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    session_id = data["session_id"]
    assert session_id is not None
    assert data["action"] == IvrAction.CONTINUE
    assert any(o["key"] == "1" for o in data["options"])

    # Step 2: Press 1 → service selection
    resp = client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": "1"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.CONTINUE
    assert len(data["options"]) >= 1
    assert any(o["key"] == "1" for o in data["options"])

    # Step 3: Press 1 → slot selection
    resp = client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": "1"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.CONTINUE
    assert len(data["options"]) >= 1

    # Step 4: Press 1 → booking confirmed
    resp = client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": "1"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == IvrAction.END
    assert "appointment" in data["prompt"].lower() or "booked" in data["prompt"].lower()

    # Verify booking was created with IVR source
    booking = db.query(Booking).filter(
        Booking.tenant_id == ivr_domain["tenant_id"],
        Booking.source == BookingSource.IVR,
    ).first()
    assert booking is not None

    # Verify SMS notification was enqueued
    outbox = db.query(NotificationOutbox).filter(
        NotificationOutbox.tenant_id == ivr_domain["tenant_id"],
    ).all()
    assert len(outbox) >= 1


def test_e2e_ivr_unknown_business_returns_404(db, admin_client):
    client, headers = admin_client

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": 99999, "caller_phone": "+48600999002"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_e2e_ivr_press_2_returns_transfer(db, admin_client, ivr_domain):
    client, headers = admin_client

    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": ivr_domain["business_id"], "caller_phone": "+48600999003"},
        headers=headers,
    )
    session_id = resp.json()["session_id"]

    resp = client.post(
        "/api/v1/ivr/simulate/press",
        json={"session_id": session_id, "key": "2"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == IvrAction.TRANSFER


def test_e2e_ivr_requires_auth(client, ivr_domain):
    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": ivr_domain["business_id"], "caller_phone": "+48600999004"},
    )
    assert resp.status_code == 401
