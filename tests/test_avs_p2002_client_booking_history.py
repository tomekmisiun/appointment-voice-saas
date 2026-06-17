"""P2-002: link bookings to clients.

A booking is associated with a client through the existing Booking ->
Customer <- Client.customer_id path (no new column on Booking — Client's
customer_id is already unique per business from P2-001).
"""
from datetime import datetime, timedelta, timezone

from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.client_service import create_client, get_bookings_for_client
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="History Salon", timezone="UTC")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    return tenant.id, biz, svc


def _book(db, tenant_id, biz, svc, customer, starts_at):
    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=starts_at,
    )


def test_get_bookings_for_client_returns_linked_customer_bookings(db):
    tenant_id, biz, svc = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48710000001")
    client_row = create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Jane", customer_id=customer.id
    )
    now = datetime.now(timezone.utc) + timedelta(days=10)
    booking1 = _book(db, tenant_id, biz, svc, customer, now)
    booking2 = _book(db, tenant_id, biz, svc, customer, now + timedelta(days=1))

    history = get_bookings_for_client(db, client_row.id, tenant_id)

    booking_ids = {b.id for b in history}
    assert booking_ids == {booking1.id, booking2.id}


def test_get_bookings_for_client_orders_newest_first(db):
    tenant_id, biz, svc = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48710000002")
    client_row = create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Jane", customer_id=customer.id
    )
    now = datetime.now(timezone.utc) + timedelta(days=10)
    earlier = _book(db, tenant_id, biz, svc, customer, now)
    later = _book(db, tenant_id, biz, svc, customer, now + timedelta(days=5))

    history = get_bookings_for_client(db, client_row.id, tenant_id)

    assert [b.id for b in history] == [later.id, earlier.id]


def test_get_bookings_for_client_without_linked_customer_is_empty(db):
    tenant_id, biz, _svc = _setup(db)
    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="No Customer Yet")

    history = get_bookings_for_client(db, client_row.id, tenant_id)

    assert history == []


def test_get_bookings_for_client_excludes_other_customers(db):
    tenant_id, biz, svc = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48710000003")
    other_customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48710000004")
    client_row = create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Jane", customer_id=customer.id
    )
    now = datetime.now(timezone.utc) + timedelta(days=10)
    own_booking = _book(db, tenant_id, biz, svc, customer, now)
    _book(db, tenant_id, biz, svc, other_customer, now)

    history = get_bookings_for_client(db, client_row.id, tenant_id)

    assert [b.id for b in history] == [own_booking.id]
