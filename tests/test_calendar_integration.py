"""Tests for the calendar integration model (AVS-F002)."""

import pytest

from sqlalchemy.exc import IntegrityError

from app.models.calendar_integration import CalendarIntegration
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.staff_service import create_staff


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Cal Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    return tenant.id, biz.id, staff.id


def test_calendar_integration_business_level_persists(db):
    tenant_id, biz_id, _staff_id = _setup(db)

    integration = CalendarIntegration(
        tenant_id=tenant_id,
        business_id=biz_id,
        provider="fake",
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    assert integration.id is not None
    assert integration.staff_id is None
    assert integration.calendar_id is None
    assert integration.is_active is True
    assert integration.created_at is not None
    assert integration.updated_at is not None


def test_calendar_integration_staff_level_persists(db):
    tenant_id, biz_id, staff_id = _setup(db)

    integration = CalendarIntegration(
        tenant_id=tenant_id,
        business_id=biz_id,
        staff_id=staff_id,
        provider="fake",
        calendar_id="staff-calendar-1",
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    assert integration.staff_id == staff_id
    assert integration.calendar_id == "staff-calendar-1"


def test_calendar_integration_unique_business_level(db):
    tenant_id, biz_id, _staff_id = _setup(db)

    db.add(CalendarIntegration(tenant_id=tenant_id, business_id=biz_id, provider="fake"))
    db.commit()

    db.add(CalendarIntegration(tenant_id=tenant_id, business_id=biz_id, provider="fake"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_calendar_integration_unique_staff_level(db):
    tenant_id, biz_id, staff_id = _setup(db)

    db.add(CalendarIntegration(
        tenant_id=tenant_id, business_id=biz_id, staff_id=staff_id, provider="fake"
    ))
    db.commit()

    db.add(CalendarIntegration(
        tenant_id=tenant_id, business_id=biz_id, staff_id=staff_id, provider="fake"
    ))
    with pytest.raises(IntegrityError):
        db.commit()


def test_calendar_integration_business_and_staff_level_coexist(db):
    tenant_id, biz_id, staff_id = _setup(db)

    db.add(CalendarIntegration(tenant_id=tenant_id, business_id=biz_id, provider="fake"))
    db.add(CalendarIntegration(
        tenant_id=tenant_id, business_id=biz_id, staff_id=staff_id, provider="fake"
    ))
    db.commit()

    results = (
        db.query(CalendarIntegration)
        .filter(CalendarIntegration.business_id == biz_id)
        .all()
    )
    assert len(results) == 2


def test_calendar_integration_query_scoped_to_tenant(db):
    tenant_id, biz_id, _staff_id = _setup(db)

    other_tenant = Tenant(slug="cal-other", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)

    db.add(CalendarIntegration(tenant_id=tenant_id, business_id=biz_id, provider="fake"))
    db.commit()

    results = (
        db.query(CalendarIntegration)
        .filter(CalendarIntegration.tenant_id == other_tenant.id)
        .all()
    )
    assert results == []
