"""P2-008: multi-service appointment model.

Adds a new, purely additive `BookingLineItem` table that can represent N
ordered services on top of a single Booking. Booking.service_id keeps its
existing meaning (the booking's primary/first service) so every existing
single-service code path (IVR, availability search, calendar sync) is
unaffected -- line items are not yet consulted anywhere except the new
booking_service.py helpers introduced here. Wiring combined-duration
availability search is a separate, later ticket (P2-009).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.domain_errors import NotFoundError
from app.models.tenant import Tenant
from app.services.booking_service import (
    add_booking_line_item,
    create_booking,
    get_booking_total_duration_minutes,
    list_booking_line_items,
)
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Multi Service Salon", timezone="UTC")
    haircut = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    color = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Color", duration_minutes=60
    )
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48720100100", name="Ola"
    )
    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=haircut.id,
        staff_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    return tenant.id, biz, haircut, color, booking


def test_booking_starts_with_no_line_items(db):
    tenant_id, _biz, _haircut, _color, booking = _setup(db)

    items = list_booking_line_items(db, booking.id, tenant_id)

    assert items == []
    assert get_booking_total_duration_minutes(db, booking.id, tenant_id) == 0


def test_add_line_item_assigns_incrementing_position(db):
    tenant_id, _biz, haircut, color, booking = _setup(db)

    first = add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=haircut.id)
    second = add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=color.id)

    assert first.position == 0
    assert second.position == 1


def test_list_line_items_ordered_by_position(db):
    tenant_id, _biz, haircut, color, booking = _setup(db)
    add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=color.id)
    add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=haircut.id)

    items = list_booking_line_items(db, booking.id, tenant_id)

    assert [i.service_id for i in items] == [color.id, haircut.id]


def test_duration_minutes_is_snapshotted_at_add_time(db):
    tenant_id, _biz, haircut, _color, booking = _setup(db)

    item = add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=haircut.id)

    assert item.duration_minutes == 30


def test_total_duration_sums_all_line_items(db):
    tenant_id, _biz, haircut, color, booking = _setup(db)
    add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=haircut.id)
    add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=color.id)

    total = get_booking_total_duration_minutes(db, booking.id, tenant_id)

    assert total == 90


def test_add_line_item_rejects_service_from_another_business(db):
    tenant_id, _biz, haircut, _color, booking = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_service = create_service(
        db, tenant_id=tenant.id, business_id=other_biz.id, name="Massage", duration_minutes=45
    )

    with pytest.raises(NotFoundError):
        add_booking_line_item(db, booking_id=booking.id, tenant_id=tenant_id, service_id=other_service.id)


def test_add_line_item_rejects_wrong_tenant_booking(db):
    tenant_id, _biz, haircut, _color, booking = _setup(db)

    with pytest.raises(NotFoundError):
        add_booking_line_item(db, booking_id=booking.id, tenant_id=999999, service_id=haircut.id)


def test_list_line_items_rejects_wrong_tenant_booking(db):
    tenant_id, _biz, haircut, _color, booking = _setup(db)

    with pytest.raises(NotFoundError):
        list_booking_line_items(db, booking.id, 999999)
