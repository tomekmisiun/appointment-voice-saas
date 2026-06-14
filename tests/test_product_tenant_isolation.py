"""Cross-tenant isolation tests for product tables (AVS-B009)."""

import uuid
from datetime import date, datetime, time, timezone

import pytest

from app.core.domain_errors import NotFoundError
from app.models.tenant import Tenant
from app.services.availability_service import get_available_slots
from app.services.booking_service import create_booking, get_booking
from app.services.business_service import create_business, get_business, list_businesses
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _create_second_tenant(db):
    slug = f"other-biz-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(slug=slug, name="Other Biz", is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def test_business_not_visible_across_tenants(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    other_tenant = _create_second_tenant(db)

    biz = create_business(
        db,
        tenant_id=default_tenant.id,
        name="Tenant A Salon",
        timezone="Europe/Warsaw",
    )

    result = get_business(db, biz.id, other_tenant.id)

    assert result is None


def test_list_businesses_scoped_to_tenant(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    other_tenant = _create_second_tenant(db)

    create_business(
        db,
        tenant_id=default_tenant.id,
        name="Tenant A Salon",
        timezone="Europe/Warsaw",
    )
    create_business(
        db,
        tenant_id=other_tenant.id,
        name="Tenant B Salon",
        timezone="Europe/Warsaw",
    )

    default_businesses = list_businesses(db, default_tenant.id)
    other_businesses = list_businesses(db, other_tenant.id)

    default_names = {b.name for b in default_businesses}
    other_names = {b.name for b in other_businesses}

    assert "Tenant A Salon" in default_names
    assert "Tenant B Salon" not in default_names
    assert "Tenant B Salon" in other_names
    assert "Tenant A Salon" not in other_names


def test_booking_not_visible_across_tenants(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    other_tenant = _create_second_tenant(db)

    biz = create_business(
        db,
        tenant_id=default_tenant.id,
        name="Salon",
        timezone="Europe/Warsaw",
    )
    staff = create_staff(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        name="Marek",
    )
    svc = create_service(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        name="Haircut",
        duration_minutes=30,
    )
    customer = get_or_create_customer(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        phone="+48600000099",
    )
    booking = create_booking(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=datetime(2026, 9, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    result = get_booking(db, booking.id, other_tenant.id)

    assert result is None


def test_api_business_not_accessible_from_other_tenant(db, client):
    register_user(client, "ta@example.com")
    promote_to_admin(db, "ta@example.com")
    token_a = login_user(client, "ta@example.com").json()["access_token"]

    other_tenant = _create_second_tenant(db)
    biz = create_business(
        db,
        tenant_id=other_tenant.id,
        name="Other Tenant Salon",
        timezone="Europe/Warsaw",
    )

    response = client.get(
        f"/api/v1/businesses/{biz.id}",
        headers=auth_headers(token_a),
    )

    assert response.status_code == 404


def test_customer_deduplication_within_tenant(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(
        db,
        tenant_id=default_tenant.id,
        name="Dedup Salon",
        timezone="Europe/Warsaw",
    )

    c1 = get_or_create_customer(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        phone="+48600000050",
        name="Jan",
    )
    c2 = get_or_create_customer(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        phone="+48600000050",
        name="Janek",
    )

    assert c1.id == c2.id


def test_same_phone_different_businesses_are_separate(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz1 = create_business(
        db,
        tenant_id=default_tenant.id,
        name="Salon One",
        timezone="Europe/Warsaw",
    )
    biz2 = create_business(
        db,
        tenant_id=default_tenant.id,
        name="Salon Two",
        timezone="Europe/Warsaw",
    )

    c1 = get_or_create_customer(
        db,
        tenant_id=default_tenant.id,
        business_id=biz1.id,
        phone="+48600000060",
    )
    c2 = get_or_create_customer(
        db,
        tenant_id=default_tenant.id,
        business_id=biz2.id,
        phone="+48600000060",
    )

    assert c1.id != c2.id


# ── AVS-C006: availability tenant/business isolation ────────────────────────

_AVAIL_DATE = date(2027, 7, 7)  # Wednesday, UTC+2 in Warsaw


def test_availability_cross_tenant_raises(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    other_tenant = _create_second_tenant(db)

    biz = create_business(db, tenant_id=default_tenant.id, name="Iso Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=default_tenant.id, business_id=biz.id, name="Iso Staff")
    svc = create_service(db, tenant_id=default_tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    create_working_hours(
        db,
        tenant_id=default_tenant.id,
        business_id=biz.id,
        staff_id=staff.id,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    with pytest.raises(NotFoundError):
        get_available_slots(
            db,
            tenant_id=other_tenant.id,
            business_id=biz.id,
            service_id=svc.id,
            staff_id=staff.id,
            query_date=_AVAIL_DATE,
        )


def test_availability_cross_business_service_raises(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()

    biz_a = create_business(db, tenant_id=default_tenant.id, name="Biz A", timezone="Europe/Warsaw")
    biz_b = create_business(db, tenant_id=default_tenant.id, name="Biz B", timezone="Europe/Warsaw")
    staff_a = create_staff(db, tenant_id=default_tenant.id, business_id=biz_a.id, name="Staff A")
    svc_b = create_service(db, tenant_id=default_tenant.id, business_id=biz_b.id, name="Biz B Svc", duration_minutes=30)
    create_working_hours(
        db,
        tenant_id=default_tenant.id,
        business_id=biz_a.id,
        staff_id=staff_a.id,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    with pytest.raises(NotFoundError):
        get_available_slots(
            db,
            tenant_id=default_tenant.id,
            business_id=biz_a.id,
            service_id=svc_b.id,  # service belongs to biz_b, not biz_a
            staff_id=staff_a.id,
            query_date=_AVAIL_DATE,
        )


def test_availability_cross_business_staff_raises(db):
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()

    biz_a = create_business(db, tenant_id=default_tenant.id, name="Biz C", timezone="Europe/Warsaw")
    biz_b = create_business(db, tenant_id=default_tenant.id, name="Biz D", timezone="Europe/Warsaw")
    staff_b = create_staff(db, tenant_id=default_tenant.id, business_id=biz_b.id, name="Staff B")
    svc_a = create_service(db, tenant_id=default_tenant.id, business_id=biz_a.id, name="Biz A Svc", duration_minutes=30)

    with pytest.raises(NotFoundError):
        get_available_slots(
            db,
            tenant_id=default_tenant.id,
            business_id=biz_a.id,
            service_id=svc_a.id,
            staff_id=staff_b.id,  # staff belongs to biz_b, not biz_a
            query_date=_AVAIL_DATE,
        )
