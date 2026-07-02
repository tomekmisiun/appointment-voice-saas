"""Tests for public booking management endpoints (PUBLIC-LINK).

Covers:
  GET  /api/v1/bookings/public/{token}  — fetch public view
  POST /api/v1/bookings/public/{token}/cancel
  POST /api/v1/bookings/public/{token}/reschedule
"""

from datetime import datetime, timezone

import pytest

from app.models.booking import BookingStatus
from app.services.booking_public_service import generate_booking_token
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff


def _dt(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def domain(db):
    from app.models.tenant import Tenant

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Public Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Bob")
    svc = create_service(db, tenant_id=tenant.id, business_id=business.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=business.id, phone="+48500000001")
    return {
        "tenant_id": tenant.id,
        "business_id": business.id,
        "staff_id": staff.id,
        "service_id": svc.id,
        "customer_id": customer.id,
    }


def _make_booking(db, domain):
    return create_booking(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        customer_id=domain["customer_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        starts_at=_dt(2030, 8, 1, 10),
    )


# ── GET public booking ────────────────────────────────────────────────────────

def test_get_public_booking_valid_token(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)

    resp = client.get(f"/api/v1/bookings/public/{token}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == booking.id
    assert data["status"] == BookingStatus.CONFIRMED
    assert "starts_at" in data
    assert "ends_at" in data
    # Public DTO must NOT expose internal IDs
    assert "tenant_id" not in data
    assert "business_id" not in data
    assert "customer_id" not in data
    assert "service_id" not in data
    assert "staff_id" not in data
    assert "source" not in data
    assert "cancel_reason" not in data
    assert "created_at" not in data


def test_get_public_booking_invalid_token_returns_404(client):
    resp = client.get("/api/v1/bookings/public/notavalidtoken")
    assert resp.status_code == 404


def test_get_public_booking_forged_signature_returns_404(client, db, domain):
    booking = _make_booking(db, domain)
    # Build a token with valid format but wrong signature
    token = f"{booking.id}.9999999999.deadbeefdeadbeef"
    resp = client.get(f"/api/v1/bookings/public/{token}")
    assert resp.status_code == 404


def test_get_public_booking_nonexistent_id_returns_404(client):
    # Generate a token for a booking that does not exist
    token = generate_booking_token(999999)
    resp = client.get(f"/api/v1/bookings/public/{token}")
    assert resp.status_code == 404


# ── POST cancel ───────────────────────────────────────────────────────────────

def test_cancel_confirmed_booking(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)

    resp = client.post(f"/api/v1/bookings/public/{token}/cancel", json={})

    assert resp.status_code == 200
    assert resp.json()["status"] == BookingStatus.CANCELLED


def test_cancel_already_cancelled_returns_409(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)

    client.post(f"/api/v1/bookings/public/{token}/cancel", json={})
    resp = client.post(f"/api/v1/bookings/public/{token}/cancel", json={})

    assert resp.status_code == 409


def test_cancel_with_bad_token_returns_404(client):
    resp = client.post("/api/v1/bookings/public/badtoken/cancel", json={})
    assert resp.status_code == 404


# ── POST reschedule ───────────────────────────────────────────────────────────

def test_reschedule_booking(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)
    new_slot = "2030-09-15T10:00:00+00:00"

    resp = client.post(
        f"/api/v1/bookings/public/{token}/reschedule",
        json={"new_starts_at": new_slot},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == BookingStatus.CONFIRMED
    # New booking has a different ID
    assert data["id"] != booking.id


def test_reschedule_cancelled_booking_returns_409(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)

    client.post(f"/api/v1/bookings/public/{token}/cancel", json={})
    resp = client.post(
        f"/api/v1/bookings/public/{token}/reschedule",
        json={"new_starts_at": "2030-09-15T10:00:00+00:00"},
    )

    assert resp.status_code == 409


def test_reschedule_naive_datetime_returns_422(client, db, domain):
    booking = _make_booking(db, domain)
    token = generate_booking_token(booking.id)

    resp = client.post(
        f"/api/v1/bookings/public/{token}/reschedule",
        json={"new_starts_at": "2030-09-15T10:00:00"},
    )

    assert resp.status_code == 422
