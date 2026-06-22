"""P3-001: salon (business-wide) opening hours, distinguished from
staff-specific hours, at the API layer.

Before this task, `POST /businesses/{business_id}/working-hours` hardcoded
`staff_id=None` -- there was no way for an admin to configure a specific
staff member's working hours through the API at all (only business-wide
"salon" hours). Staff-specific hours could only be created via a direct
service-layer call, which is how seed scripts/tests set them up but not
how a real business owner would. This adds `staff_id` to the create
request (optional, defaults to business-wide), with the same
business-membership validation as other `staff_id`-accepting endpoints.

See `docs/appointment-saas-roadmap.md` P3-001 and
`docs/audits/pre-p3-readiness-audit.md` §9.
"""
from datetime import time

import pytest

from app.core.domain_errors import NotFoundError
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours, list_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Hours Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")
    return {"tenant_id": tenant.id, "business_id": business.id, "staff_id": staff.id}


# --- service layer ---


def test_create_business_wide_hours(db, domain):
    wh = create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    assert wh.staff_id is None


def test_create_staff_specific_hours(db, domain):
    wh = create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    assert wh.staff_id == domain["staff_id"]


def test_create_hours_rejects_staff_from_another_business(db, domain):
    other_business = create_business(
        db, tenant_id=domain["tenant_id"], name="Other Salon", timezone="UTC"
    )
    foreign_staff = create_staff(
        db, tenant_id=domain["tenant_id"], business_id=other_business.id, name="Foreign"
    )

    with pytest.raises(NotFoundError):
        create_working_hours(
            db,
            tenant_id=domain["tenant_id"],
            business_id=domain["business_id"],
            staff_id=foreign_staff.id,
            day_of_week=1,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )


def test_list_hours_staff_id_filter_returns_only_that_staff_member(db, domain):
    """staff_id=None means "no filter" (matches list_availability_exceptions'
    convention) -- it returns business-wide *and* staff-specific rows
    together. Passing a real staff_id, however, returns only that staff
    member's rows, never another staff member's or the business-wide ones."""
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"], staff_id=None,
        day_of_week=1, start_time=time(9, 0), end_time=time(17, 0),
    )
    create_working_hours(
        db, tenant_id=domain["tenant_id"], business_id=domain["business_id"],
        staff_id=domain["staff_id"], day_of_week=1, start_time=time(10, 0), end_time=time(16, 0),
    )

    unfiltered = list_working_hours(db, domain["business_id"], domain["tenant_id"], staff_id=None)
    staff_specific = list_working_hours(
        db, domain["business_id"], domain["tenant_id"], staff_id=domain["staff_id"]
    )

    assert {wh.staff_id for wh in unfiltered} == {None, domain["staff_id"]}
    assert {wh.staff_id for wh in staff_specific} == {domain["staff_id"]}


# --- API layer ---


def _admin_token(db, client, email: str) -> str:
    register_user(client, email)
    promote_to_admin(db, email)
    return login_user(client, email).json()["access_token"]


def test_create_business_wide_hours_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin_token(db, client, "salon-hours-admin@example.com")
    business = create_business(db, tenant_id=tenant.id, name="API Salon", timezone="UTC")

    resp = client.post(
        f"/api/v1/businesses/{business.id}/working-hours",
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 201
    assert resp.json()["staff_id"] is None


def test_create_staff_specific_hours_api(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin_token(db, client, "staff-hours-admin@example.com")
    business = create_business(db, tenant_id=tenant.id, name="API Salon 2", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Marek")

    resp = client.post(
        f"/api/v1/businesses/{business.id}/working-hours",
        json={
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "staff_id": staff.id,
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 201
    assert resp.json()["staff_id"] == staff.id


def test_create_hours_api_rejects_staff_from_another_business(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin_token(db, client, "cross-hours-admin@example.com")
    business_a = create_business(db, tenant_id=tenant.id, name="Biz A", timezone="UTC")
    business_b = create_business(db, tenant_id=tenant.id, name="Biz B", timezone="UTC")
    staff_b = create_staff(db, tenant_id=tenant.id, business_id=business_b.id, name="Staff B")

    resp = client.post(
        f"/api/v1/businesses/{business_a.id}/working-hours",
        json={
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "staff_id": staff_b.id,
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_list_hours_api_filters_by_staff_id(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin_token(db, client, "list-hours-admin@example.com")
    business = create_business(db, tenant_id=tenant.id, name="List Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Anna")

    client.post(
        f"/api/v1/businesses/{business.id}/working-hours",
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )
    client.post(
        f"/api/v1/businesses/{business.id}/working-hours",
        json={
            "day_of_week": 1,
            "start_time": "10:00:00",
            "end_time": "16:00:00",
            "staff_id": staff.id,
        },
        headers=auth_headers(token),
    )

    resp = client.get(
        f"/api/v1/businesses/{business.id}/working-hours",
        params={"staff_id": staff.id},
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["staff_id"] == staff.id
