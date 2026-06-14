"""Cross-tenant isolation tests for product tables (AVS-B009)."""

import uuid

from app.models.tenant import Tenant
from app.services.business_service import create_business, get_business, list_businesses
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.booking_service import create_booking, get_booking
from tests.database import auth_headers, login_user, promote_to_admin, register_user

from datetime import datetime, timezone


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
