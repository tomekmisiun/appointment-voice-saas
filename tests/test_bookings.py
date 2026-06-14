"""Tests for Booking engine (AVS-B007, AVS-D001-D007)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import BookingStatus
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _dt(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def domain_setup(db):
    from app.models.tenant import Tenant

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(
        db,
        tenant_id=tenant.id,
        name="Test Salon",
        timezone="Europe/Warsaw",
    )
    staff = create_staff(
        db,
        tenant_id=tenant.id,
        business_id=business.id,
        name="Marek",
    )
    svc = create_service(
        db,
        tenant_id=tenant.id,
        business_id=business.id,
        name="Haircut",
        duration_minutes=30,
    )
    customer = get_or_create_customer(
        db,
        tenant_id=tenant.id,
        business_id=business.id,
        phone="+48600000001",
        name="Jan",
    )
    return {
        "tenant_id": tenant.id,
        "business_id": business.id,
        "staff_id": staff.id,
        "service_id": svc.id,
        "customer_id": customer.id,
    }


def test_create_booking(db, domain_setup):
    s = domain_setup
    booking = create_booking(
        db,
        tenant_id=s["tenant_id"],
        business_id=s["business_id"],
        customer_id=s["customer_id"],
        service_id=s["service_id"],
        staff_id=s["staff_id"],
        starts_at=_dt(2026, 7, 1, 9),
    )

    assert booking.id is not None
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.ends_at == _dt(2026, 7, 1, 9) + timedelta(minutes=30)


def test_cancel_booking(db, domain_setup):
    s = domain_setup
    booking = create_booking(
        db,
        tenant_id=s["tenant_id"],
        business_id=s["business_id"],
        customer_id=s["customer_id"],
        service_id=s["service_id"],
        staff_id=s["staff_id"],
        starts_at=_dt(2026, 7, 1, 10),
    )

    cancelled = cancel_booking(db, booking.id, s["tenant_id"], reason="Customer request")

    assert cancelled.status == BookingStatus.CANCELLED
    assert cancelled.cancel_reason == "Customer request"


def test_double_booking_rejected(db, domain_setup):
    from app.core.domain_errors import ConflictError

    s = domain_setup
    create_booking(
        db,
        tenant_id=s["tenant_id"],
        business_id=s["business_id"],
        customer_id=s["customer_id"],
        service_id=s["service_id"],
        staff_id=s["staff_id"],
        starts_at=_dt(2026, 7, 2, 9),
    )

    with pytest.raises(ConflictError):
        create_booking(
            db,
            tenant_id=s["tenant_id"],
            business_id=s["business_id"],
            customer_id=s["customer_id"],
            service_id=s["service_id"],
            staff_id=s["staff_id"],
            starts_at=_dt(2026, 7, 2, 9),
        )


def test_non_overlapping_bookings_allowed(db, domain_setup):
    s = domain_setup
    b1 = create_booking(
        db,
        tenant_id=s["tenant_id"],
        business_id=s["business_id"],
        customer_id=s["customer_id"],
        service_id=s["service_id"],
        staff_id=s["staff_id"],
        starts_at=_dt(2026, 7, 3, 9),
    )
    b2 = create_booking(
        db,
        tenant_id=s["tenant_id"],
        business_id=s["business_id"],
        customer_id=s["customer_id"],
        service_id=s["service_id"],
        staff_id=s["staff_id"],
        starts_at=_dt(2026, 7, 3, 10),
    )

    assert b1.id != b2.id


def test_booking_api_create_and_cancel(db, client):
    register_user(client, "bk1@example.com")
    promote_to_admin(db, "bk1@example.com")
    token = login_user(client, "bk1@example.com").json()["access_token"]

    biz = client.post(
        "/api/v1/businesses",
        json={"name": "API Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    svc = client.post(
        f"/api/v1/businesses/{biz['id']}/services",
        json={"name": "Trim", "duration_minutes": 15},
        headers=auth_headers(token),
    ).json()

    from app.services.customer_service import get_or_create_customer
    from app.models.tenant import Tenant

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    customer = get_or_create_customer(
        db,
        tenant_id=tenant.id,
        business_id=biz["id"],
        phone="+48700000001",
    )

    booking_resp = client.post(
        f"/api/v1/businesses/{biz['id']}/bookings",
        json={
            "customer_id": customer.id,
            "service_id": svc["id"],
            "starts_at": "2026-08-01T09:00:00+00:00",
        },
        headers=auth_headers(token),
    )
    assert booking_resp.status_code == 201
    booking = booking_resp.json()
    assert booking["status"] == "confirmed"

    cancel_resp = client.post(
        f"/api/v1/businesses/{biz['id']}/bookings/{booking['id']}/cancel",
        json={"reason": "No show"},
        headers=auth_headers(token),
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
