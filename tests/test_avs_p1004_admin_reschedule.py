"""P1-004: reschedule a booking via the admin/business API.

reschedule_booking() cancels the existing booking and creates a new one at
the new time (same service/staff/customer) — see booking_service.py for why
this is cancel+create rather than an in-place time update: the calendar
adapter only supports create/cancel, not updating an already-synced event.
"""
from datetime import datetime, timedelta, timezone

from app.models.booking import BookingSource, BookingStatus
from app.models.tenant import Tenant
from app.services.booking_service import create_booking, reschedule_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _dt(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reschedule API Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Marek")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48650000001")
    return tenant.id, biz, staff, svc, customer


def test_reschedule_booking_cancels_old_and_creates_new(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    old = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_dt(2027, 1, 5, 9),
    )

    new = reschedule_booking(
        db, old.id, biz.id, tenant_id, new_starts_at=_dt(2027, 1, 6, 14), reason="staff request"
    )

    db.refresh(old)
    assert old.status == BookingStatus.CANCELLED
    assert old.cancel_reason == "staff request"
    assert new.id != old.id
    assert new.status == BookingStatus.CONFIRMED
    assert new.starts_at == _dt(2027, 1, 6, 14)
    assert new.ends_at == _dt(2027, 1, 6, 14) + timedelta(minutes=30)
    assert new.service_id == svc.id
    assert new.staff_id == staff.id
    assert new.customer_id == customer.id


def test_reschedule_booking_uses_given_source(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    old = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 1, 7, 9),
        source=BookingSource.IVR,
    )

    new = reschedule_booking(
        db, old.id, biz.id, tenant_id, new_starts_at=_dt(2027, 1, 7, 10), source=BookingSource.API
    )

    assert new.source == BookingSource.API


def test_reschedule_already_cancelled_booking_raises(db):
    from app.core.domain_errors import ConflictError
    from app.services.booking_service import cancel_booking

    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 1, 8, 9),
    )
    cancel_booking(db, booking.id, biz.id, tenant_id)

    try:
        reschedule_booking(db, booking.id, biz.id, tenant_id, new_starts_at=_dt(2027, 1, 8, 10))
        raise AssertionError("expected ConflictError")
    except ConflictError:
        pass


def test_reschedule_booking_api_endpoint(db, client):
    register_user(client, "resched_admin@example.com")
    promote_to_admin(db, "resched_admin@example.com")
    token = login_user(client, "resched_admin@example.com").json()["access_token"]

    biz = client.post(
        "/api/v1/businesses",
        json={"name": "API Reschedule Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    svc = client.post(
        f"/api/v1/businesses/{biz['id']}/services",
        json={"name": "Trim", "duration_minutes": 15},
        headers=auth_headers(token),
    ).json()

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz["id"], phone="+48650000099"
    )

    booking_resp = client.post(
        f"/api/v1/businesses/{biz['id']}/bookings",
        json={
            "customer_id": customer.id,
            "service_id": svc["id"],
            "starts_at": "2027-02-01T09:00:00+00:00",
        },
        headers=auth_headers(token),
    )
    booking = booking_resp.json()

    resched_resp = client.post(
        f"/api/v1/businesses/{biz['id']}/bookings/{booking['id']}/reschedule",
        json={"new_starts_at": "2027-02-02T11:00:00+00:00", "reason": "customer asked"},
        headers=auth_headers(token),
    )

    assert resched_resp.status_code == 200
    new_booking = resched_resp.json()
    assert new_booking["id"] != booking["id"]
    assert new_booking["status"] == "confirmed"
    assert new_booking["starts_at"] == "2027-02-02T11:00:00Z"

    old_resp = client.get(
        f"/api/v1/businesses/{biz['id']}/bookings/{booking['id']}",
        headers=auth_headers(token),
    )
    assert old_resp.json()["status"] == "cancelled"


def test_reschedule_booking_api_requires_admin(db, client):
    register_user(client, "resched_member@example.com")
    token = login_user(client, "resched_member@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 1, 9, 9),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/reschedule",
        json={"new_starts_at": "2027-01-10T10:00:00+00:00"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 403


def test_reschedule_booking_api_rejects_naive_datetime(db, client):
    register_user(client, "resched_naive@example.com")
    promote_to_admin(db, "resched_naive@example.com")
    token = login_user(client, "resched_naive@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 1, 11, 9),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/reschedule",
        json={"new_starts_at": "2027-01-12T10:00:00"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 422
