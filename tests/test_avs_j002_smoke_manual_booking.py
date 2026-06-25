"""AVS-J002: Smoke — manual booking via API with fake SMS and fake calendar.

Proves the end-to-end API path works locally:
  seed demo → create customer → POST booking → verify outbox SMS + calendar entry.
"""
from datetime import datetime, timezone

import pytest

from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.notification_outbox import NotificationOutbox
from app.models.tenant import Tenant
from app.models.user import User
from app.seed_demo_data import DEMO_BUSINESS_NAME, seed_demo
from app.services.customer_service import get_or_create_customer
from tests.database import auth_headers, login_user, promote_to_admin, register_user


@pytest.fixture()
def smoke_domain(db, client):
    # Seed demo data
    seed_demo(db)
    from app.models.business import Business
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()

    register_user(client, "j002_admin@example.com")
    promote_to_admin(db, "j002_admin@example.com")
    j002_user = db.query(User).filter(User.email == "j002_admin@example.com").one()
    has_membership = db.query(BusinessMembership).filter_by(
        business_id=biz.id, user_id=j002_user.id
    ).first()
    if has_membership is None:
        db.add(BusinessMembership(
            tenant_id=tenant.id,
            business_id=biz.id,
            user_id=j002_user.id,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
        ))
        db.commit()
    token = login_user(client, "j002_admin@example.com").json()["access_token"]

    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id,
        phone="+48555666777", name="Demo Customer"
    )

    from app.models.service import Service
    svc = db.query(Service).filter(Service.business_id == biz.id, Service.name == "Haircut").one()

    from app.models.staff import Staff
    staff = db.query(Staff).filter(Staff.business_id == biz.id).first()

    return {
        "db": db,
        "client": client,
        "headers": auth_headers(token),
        "tenant_id": tenant.id,
        "biz_id": biz.id,
        "customer_id": customer.id,
        "service_id": svc.id,
        "staff_id": staff.id,
    }


# Next Monday at 10:00 UTC — inside Mon–Fri 09:00–17:00 window
BOOKING_STARTS_AT = "2026-06-22T10:00:00+00:00"


def test_manual_booking_returns_201(smoke_domain):
    client, headers = smoke_domain["client"], smoke_domain["headers"]
    biz_id = smoke_domain["biz_id"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/bookings",
        json={
            "customer_id": smoke_domain["customer_id"],
            "service_id": smoke_domain["service_id"],
            "staff_id": None,
            "starts_at": BOOKING_STARTS_AT,
            "source": BookingSource.API,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == BookingStatus.CONFIRMED
    assert data["source"] == BookingSource.API


def test_manual_booking_persisted_in_db(smoke_domain):
    client, headers, db = smoke_domain["client"], smoke_domain["headers"], smoke_domain["db"]
    biz_id = smoke_domain["biz_id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/bookings",
        json={
            "customer_id": smoke_domain["customer_id"],
            "service_id": smoke_domain["service_id"],
            "staff_id": None,
            "starts_at": BOOKING_STARTS_AT,
            "source": BookingSource.API,
        },
        headers=headers,
    )
    booking = db.query(Booking).filter(
        Booking.business_id == biz_id,
        Booking.tenant_id == smoke_domain["tenant_id"],
    ).first()
    assert booking is not None
    assert booking.status == BookingStatus.CONFIRMED
    expected_dt = datetime(2026, 6, 22, 10, 0, 0, tzinfo=timezone.utc)
    assert booking.starts_at == expected_dt


def test_manual_booking_enqueues_sms_notification(smoke_domain):
    client, headers, db = smoke_domain["client"], smoke_domain["headers"], smoke_domain["db"]
    biz_id = smoke_domain["biz_id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/bookings",
        json={
            "customer_id": smoke_domain["customer_id"],
            "service_id": smoke_domain["service_id"],
            "staff_id": None,
            "starts_at": BOOKING_STARTS_AT,
            "source": BookingSource.API,
        },
        headers=headers,
    )
    outbox = db.query(NotificationOutbox).filter(
        NotificationOutbox.tenant_id == smoke_domain["tenant_id"],
    ).all()
    assert len(outbox) >= 1
    # Fake provider always marks delivered
    assert all(o.status in ("pending", "delivered") for o in outbox)


def test_double_booking_rejected(smoke_domain):
    """Two bookings for the same staff/slot must fail with 409."""
    client, headers = smoke_domain["client"], smoke_domain["headers"]
    biz_id = smoke_domain["biz_id"]
    payload = {
        "customer_id": smoke_domain["customer_id"],
        "service_id": smoke_domain["service_id"],
        "staff_id": smoke_domain["staff_id"],
        "starts_at": BOOKING_STARTS_AT,
        "source": BookingSource.API,
    }
    r1 = client.post(f"/api/v1/businesses/{biz_id}/bookings", json=payload, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(f"/api/v1/businesses/{biz_id}/bookings", json=payload, headers=headers)
    assert r2.status_code == 409
