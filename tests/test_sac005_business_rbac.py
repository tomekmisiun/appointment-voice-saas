"""SAC-005: per-business RBAC via BusinessMembership.role.

Tests the require_business_role() dependency wired into services, staff,
bookings, working-hours, and similar per-business routes.

Contract:
  - Tenant admin (User.role == "admin") always passes — existing behaviour
    preserved; no membership row is required.
  - Platform admin (User.role == "platform_admin") always passes.
  - Regular user (User.role == "user") without an active BusinessMembership
    gets 403 on any per-business endpoint.
  - Regular user with BusinessMembership.role == "staff" can list/read
    (min_role="staff") but not mutate (min_role="admin").
  - Regular user with BusinessMembership.role == "admin" can mutate.
  - Regular user with BusinessMembership.role == "owner" can mutate.
  - Membership with status != "active" (invited, suspended, revoked) still
    gets 403.
"""

import pytest

from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="RBAC Salon", timezone="UTC")
    service = create_service(
        db,
        tenant_id=tenant.id,
        business_id=business.id,
        name="Haircut",
        duration_minutes=30,
    )
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Alice")
    return {
        "tenant_id": tenant.id,
        "business_id": business.id,
        "service_id": service.id,
        "staff_id": staff.id,
    }


def _make_membership(
    db,
    tenant_id: int,
    business_id: int,
    user_id: int,
    role: str,
    status: str = MembershipStatus.ACTIVE,
    staff_id: int | None = None,
):
    m = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user_id,
        role=role,
        status=status,
        staff_id=staff_id,
    )
    db.add(m)
    db.commit()


def _register_and_login(client, email: str) -> str:
    register_user(client, email)
    resp = login_user(client, email)
    return resp.json()["access_token"]


# ── tenant admin bypass ───────────────────────────────────────────────────────

def test_tenant_admin_can_create_service_without_membership(db, client, domain):
    register_user(client, "admin@sac005.test")
    promote_to_admin(db, "admin@sac005.test")
    token = login_user(client, "admin@sac005.test").json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Color", "duration_minutes": 60},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201


def test_tenant_admin_can_list_services_without_membership(db, client, domain):
    register_user(client, "admin2@sac005.test")
    promote_to_admin(db, "admin2@sac005.test")
    token = login_user(client, "admin2@sac005.test").json()["access_token"]

    resp = client.get(
        f"/api/v1/businesses/{domain['business_id']}/services",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200


# ── no membership → 403 on mutating endpoints ─────────────────────────────────

def test_user_without_membership_cannot_create_service(client, domain):
    token = _register_and_login(client, "nomember@sac005.test")

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Perm", "duration_minutes": 90},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_user_without_membership_cannot_delete_service(client, domain):
    token = _register_and_login(client, "nomember2@sac005.test")

    resp = client.delete(
        f"/api/v1/businesses/{domain['business_id']}/services/{domain['service_id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


# ── staff-role: read allowed, write denied ────────────────────────────────────

def test_staff_member_can_list_services(db, client, domain):
    register_user(client, "staff@sac005.test")
    from app.models.user import User
    user = db.query(User).filter(User.email == "staff@sac005.test").one()
    _make_membership(db, domain["tenant_id"], domain["business_id"], user.id, MembershipRole.STAFF, staff_id=domain["staff_id"])
    token = login_user(client, "staff@sac005.test").json()["access_token"]

    resp = client.get(
        f"/api/v1/businesses/{domain['business_id']}/services",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200


def test_staff_member_cannot_create_service(db, client, domain):
    register_user(client, "staff2@sac005.test")
    from app.models.user import User
    user = db.query(User).filter(User.email == "staff2@sac005.test").one()
    _make_membership(db, domain["tenant_id"], domain["business_id"], user.id, MembershipRole.STAFF, staff_id=domain["staff_id"])
    token = login_user(client, "staff2@sac005.test").json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Nail", "duration_minutes": 45},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


# ── admin-role member: full write access ─────────────────────────────────────

def test_business_admin_member_can_create_service(db, client, domain):
    register_user(client, "bizadmin@sac005.test")
    from app.models.user import User
    user = db.query(User).filter(User.email == "bizadmin@sac005.test").one()
    _make_membership(db, domain["tenant_id"], domain["business_id"], user.id, MembershipRole.ADMIN)
    token = login_user(client, "bizadmin@sac005.test").json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Brow", "duration_minutes": 20},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201


def test_business_owner_member_can_create_service(db, client, domain):
    register_user(client, "bizowner@sac005.test")
    from app.models.user import User
    user = db.query(User).filter(User.email == "bizowner@sac005.test").one()
    _make_membership(db, domain["tenant_id"], domain["business_id"], user.id, MembershipRole.OWNER)
    token = login_user(client, "bizowner@sac005.test").json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Facial", "duration_minutes": 60},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201


# ── inactive membership statuses are rejected ─────────────────────────────────

@pytest.mark.parametrize("bad_status", [
    MembershipStatus.INVITED,
    MembershipStatus.SUSPENDED,
    MembershipStatus.REVOKED,
])
def test_inactive_membership_cannot_mutate(db, client, domain, bad_status):
    email = f"inactive_{bad_status}@sac005.test"
    register_user(client, email)
    from app.models.user import User
    user = db.query(User).filter(User.email == email).one()
    _make_membership(
        db, domain["tenant_id"], domain["business_id"], user.id,
        MembershipRole.ADMIN, status=bad_status,
    )
    token = login_user(client, email).json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{domain['business_id']}/services",
        json={"name": "Test", "duration_minutes": 30},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403
