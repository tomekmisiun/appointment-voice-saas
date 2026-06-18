"""P2-010: waitlist data model.

A WaitlistEntry records a customer's desire for a service (and optionally
a specific staff member) on a given date, recorded when no slot was
available. This is purely the data model + basic CRUD: nothing creates
these from the cancellation flow or offers them automatically (P2-011),
and nothing expires/escalates them yet (P2-012).
"""
from datetime import date, timedelta

import pytest

from app.core.domain_errors import NotFoundError
from app.models.tenant import Tenant
from app.models.waitlist_entry import WaitlistEntryStatus
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.waitlist_service import (
    create_waitlist_entry,
    list_waitlist_entries,
    require_waitlist_entry,
    update_waitlist_entry_status,
)


def _future_date(days: int = 7) -> date:
    return date.today() + timedelta(days=days)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Waitlist Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48740000001", name="Eager Customer"
    )
    return tenant.id, biz, svc, customer


def test_create_waitlist_entry_defaults_to_waiting(db):
    tenant_id, biz, svc, customer = _setup(db)

    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(),
    )

    assert entry.id is not None
    assert entry.status == WaitlistEntryStatus.WAITING
    assert entry.staff_id is None


def test_create_waitlist_entry_with_preferred_staff(db):
    tenant_id, biz, svc, customer = _setup(db)
    staff = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist")

    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(), staff_id=staff.id,
    )

    assert entry.staff_id == staff.id


def test_create_waitlist_entry_rejects_service_from_another_business(db):
    tenant_id, biz, svc, customer = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_svc = create_service(
        db, tenant_id=tenant.id, business_id=other_biz.id, name="Massage", duration_minutes=45
    )

    with pytest.raises(NotFoundError):
        create_waitlist_entry(
            db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
            service_id=other_svc.id, desired_date=_future_date(),
        )


def test_create_waitlist_entry_rejects_customer_from_another_business(db):
    tenant_id, biz, svc, customer = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=other_biz.id, phone="+48740000002", name="Other"
    )

    with pytest.raises(NotFoundError):
        create_waitlist_entry(
            db, tenant_id=tenant_id, business_id=biz.id, customer_id=other_customer.id,
            service_id=svc.id, desired_date=_future_date(),
        )


def test_create_waitlist_entry_rejects_staff_from_another_business(db):
    tenant_id, biz, svc, customer = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_staff = create_staff(db, tenant_id=tenant.id, business_id=other_biz.id, name="Other Stylist")

    with pytest.raises(NotFoundError):
        create_waitlist_entry(
            db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
            service_id=svc.id, desired_date=_future_date(), staff_id=other_staff.id,
        )


def test_list_waitlist_entries_scoped_to_business(db):
    tenant_id, biz, svc, customer = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_svc = create_service(
        db, tenant_id=tenant.id, business_id=other_biz.id, name="Massage", duration_minutes=45
    )
    other_customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=other_biz.id, phone="+48740000003", name="Other"
    )
    create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(),
    )
    create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=other_biz.id, customer_id=other_customer.id,
        service_id=other_svc.id, desired_date=_future_date(),
    )

    entries = list_waitlist_entries(db, biz.id, tenant_id)

    assert len(entries) == 1
    assert entries[0].business_id == biz.id


def test_list_waitlist_entries_filters_by_status(db):
    tenant_id, biz, svc, customer = _setup(db)
    waiting = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(),
    )
    offered = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(8),
    )
    update_waitlist_entry_status(db, offered.id, tenant_id, status=WaitlistEntryStatus.OFFERED)

    waiting_entries = list_waitlist_entries(db, biz.id, tenant_id, status=WaitlistEntryStatus.WAITING)

    assert [e.id for e in waiting_entries] == [waiting.id]


def test_update_waitlist_entry_status_transitions(db):
    tenant_id, biz, svc, customer = _setup(db)
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(),
    )

    updated = update_waitlist_entry_status(db, entry.id, tenant_id, status=WaitlistEntryStatus.OFFERED)
    assert updated.status == WaitlistEntryStatus.OFFERED

    updated = update_waitlist_entry_status(db, entry.id, tenant_id, status=WaitlistEntryStatus.CONFIRMED)
    assert updated.status == WaitlistEntryStatus.CONFIRMED


def test_require_waitlist_entry_rejects_wrong_tenant(db):
    tenant_id, biz, svc, customer = _setup(db)
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(),
    )

    with pytest.raises(NotFoundError):
        require_waitlist_entry(db, entry.id, 999999)
