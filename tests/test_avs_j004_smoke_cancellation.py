"""AVS-J004: Smoke — booking cancellation with notification and calendar side-effects.

Proves cancel flow works locally:
  create booking → cancel via API → booking CANCELLED in DB,
  cancellation SMS enqueued.
"""
import pytest

from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.notification_outbox import NotificationOutbox
from app.models.tenant import Tenant
from app.models.user import User
from app.seed_demo_data import DEMO_BUSINESS_NAME, seed_demo
from app.services.customer_service import get_or_create_customer
from tests.database import auth_headers, login_user, promote_to_admin, register_user


BOOKING_STARTS_AT = "2026-06-23T11:00:00+00:00"  # Tuesday inside Mon–Fri window


@pytest.fixture()
def cancel_domain(db, client):
    seed_demo(db)
    from app.models.business import Business
    from app.models.service import Service
    from app.models.staff import Staff

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).one()

    register_user(client, "j004_admin@example.com")
    promote_to_admin(db, "j004_admin@example.com")
    j004_user = db.query(User).filter(User.email == "j004_admin@example.com").one()
    has_membership = db.query(BusinessMembership).filter_by(
        business_id=biz.id, user_id=j004_user.id
    ).first()
    if has_membership is None:
        db.add(BusinessMembership(
            tenant_id=tenant.id,
            business_id=biz.id,
            user_id=j004_user.id,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
        ))
        db.commit()
    token = login_user(client, "j004_admin@example.com").json()["access_token"]
    headers = auth_headers(token)

    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id,
        phone="+48555666888", name="Cancel Customer"
    )
    svc = db.query(Service).filter(Service.business_id == biz.id, Service.name == "Haircut").one()
    staff = db.query(Staff).filter(Staff.business_id == biz.id).first()

    # Create a booking to cancel
    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings",
        json={
            "customer_id": customer.id,
            "service_id": svc.id,
            "staff_id": staff.id,
            "starts_at": BOOKING_STARTS_AT,
            "source": BookingSource.API,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    booking_id = resp.json()["id"]

    return {
        "db": db,
        "client": client,
        "headers": headers,
        "tenant_id": tenant.id,
        "biz_id": biz.id,
        "booking_id": booking_id,
    }


def test_cancel_returns_200_with_cancelled_status(cancel_domain):
    client, headers = cancel_domain["client"], cancel_domain["headers"]
    biz_id, booking_id = cancel_domain["biz_id"], cancel_domain["booking_id"]

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/bookings/{booking_id}/cancel",
        json={"reason": "customer request"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == BookingStatus.CANCELLED


def test_cancel_persists_cancelled_status_in_db(cancel_domain):
    client, headers, db = cancel_domain["client"], cancel_domain["headers"], cancel_domain["db"]
    biz_id, booking_id = cancel_domain["biz_id"], cancel_domain["booking_id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/bookings/{booking_id}/cancel",
        json={"reason": "no show"},
        headers=headers,
    )
    booking = db.get(Booking, booking_id)
    db.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancel_reason == "no show"


def test_cancel_enqueues_cancellation_notification(cancel_domain):
    client, headers, db = cancel_domain["client"], cancel_domain["headers"], cancel_domain["db"]
    biz_id, booking_id = cancel_domain["biz_id"], cancel_domain["booking_id"]
    tid = cancel_domain["tenant_id"]

    outbox_before = db.query(NotificationOutbox).filter(
        NotificationOutbox.tenant_id == tid
    ).count()

    client.post(
        f"/api/v1/businesses/{biz_id}/bookings/{booking_id}/cancel",
        json={"reason": "rescheduled"},
        headers=headers,
    )

    outbox_after = db.query(NotificationOutbox).filter(
        NotificationOutbox.tenant_id == tid
    ).count()
    assert outbox_after > outbox_before


def test_cancel_twice_returns_409(cancel_domain):
    client, headers = cancel_domain["client"], cancel_domain["headers"]
    biz_id, booking_id = cancel_domain["biz_id"], cancel_domain["booking_id"]

    client.post(
        f"/api/v1/businesses/{biz_id}/bookings/{booking_id}/cancel",
        json={"reason": "first"},
        headers=headers,
    )
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/bookings/{booking_id}/cancel",
        json={"reason": "second"},
        headers=headers,
    )
    assert resp.status_code == 409
