"""SAC-005: membership-based RBAC tests.

Covers the RBAC matrix for business-scoped mutations, cross-business IDOR,
session invalidation on revoke/suspend, and platform-admin bypass.

All write tests use POST /api/v1/businesses/{business_id}/services as the
representative mutating endpoint -- it is behind require_business_member(OWNER,
ADMIN) and has the simplest body.
"""
import uuid

from app.models.business import Business
from app.models.business_membership import (
    BusinessMembership,
    MembershipRole,
    MembershipStatus,
)
from app.models.staff import Staff
from app.models.user import User
from app.services.membership_service import revoke_membership, suspend_membership
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _email(prefix: str = "rbac") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _setup_owner(db, client) -> tuple[str, int]:
    """Register → admin role → login → create business (auto-creates OWNER membership)."""
    email = _email("owner")
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "Salon", "timezone": "UTC"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def _create_service_payload() -> dict:
    return {"name": f"Cut-{uuid.uuid4().hex[:6]}", "duration_minutes": 30}


# ---------------------------------------------------------------------------
# Happy path: OWNER and ADMIN memberships grant write access
# ---------------------------------------------------------------------------

def test_owner_membership_can_create_service(db, client):
    token, biz_id = _setup_owner(db, client)

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(token),
    )

    assert resp.status_code == 201


def test_admin_membership_can_create_service(db, client):
    """A user with an explicit ADMIN membership (not OWNER) can also mutate."""
    _, biz_id = _setup_owner(db, client)

    # Create a second user and give them a direct ADMIN membership via DB.
    email = _email("admin")
    register_user(client, email)
    promote_to_admin(db, email)
    admin_user = db.query(User).filter(User.email == email).one()
    biz = db.query(Business).filter(Business.id == biz_id).one()
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz_id,
        user_id=admin_user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()

    admin_token = login_user(client, email).json()["access_token"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(admin_token),
    )

    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 403: insufficient membership
# ---------------------------------------------------------------------------

def test_no_membership_returns_403(db, client):
    """A user with User.role='admin' but no BusinessMembership is rejected."""
    _, biz_id = _setup_owner(db, client)

    email = _email("nomember")
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(token),
    )

    assert resp.status_code == 403


def test_staff_membership_returns_403_on_write(db, client):
    """A STAFF-role membership cannot execute write operations."""
    _, biz_id = _setup_owner(db, client)
    biz = db.query(Business).filter(Business.id == biz_id).one()

    email = _email("staff")
    register_user(client, email)
    staff_user = db.query(User).filter(User.email == email).one()

    # STAFF role requires a staff_id (check constraint).
    staff_record = Staff(
        tenant_id=biz.tenant_id,
        business_id=biz_id,
        name="Worker",
        is_active=True,
    )
    db.add(staff_record)
    db.flush()
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz_id,
        user_id=staff_user.id,
        staff_id=staff_record.id,
        role=MembershipRole.STAFF,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()

    token = login_user(client, email).json()["access_token"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(token),
    )

    assert resp.status_code == 403


def test_suspended_membership_invalidates_token(db, client):
    """suspend_membership increments token_version like revoke: the old
    session token becomes stale (401), forcing re-login. On fresh login the
    SUSPENDED status causes 403, enforcing a two-step access barrier."""
    token, biz_id = _setup_owner(db, client)
    biz = db.query(Business).filter(Business.id == biz_id).one()

    email = _email("suspended")
    register_user(client, email)
    suspended_user = db.query(User).filter(User.email == email).one()
    membership = BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz_id,
        user_id=suspended_user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.commit()

    suspended_token = login_user(client, email).json()["access_token"]
    suspend_membership(db, membership)
    db.commit()

    # Old token is stale after token_version bump → 401
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(suspended_token),
    )
    assert resp.status_code == 401

    # Fresh login with new token_version → membership is SUSPENDED → 403
    fresh_token = login_user(client, email).json()["access_token"]
    resp2 = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(fresh_token),
    )
    assert resp2.status_code == 403


# ---------------------------------------------------------------------------
# 401: revoked membership increments token_version → stale token rejected
# ---------------------------------------------------------------------------

def test_revoked_membership_invalidates_token(db, client):
    token, biz_id = _setup_owner(db, client)
    biz = db.query(Business).filter(Business.id == biz_id).one()

    email = _email("revoked")
    register_user(client, email)
    revoked_user = db.query(User).filter(User.email == email).one()
    membership = BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz_id,
        user_id=revoked_user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.commit()

    revoked_token = login_user(client, email).json()["access_token"]

    # Revoke invalidates the session by incrementing token_version.
    revoke_membership(db, membership, revoked_by_user_id=revoked_user.id)
    db.commit()

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(revoked_token),
    )

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# IDOR: cross-business access denied
# ---------------------------------------------------------------------------

def test_membership_for_other_business_is_rejected(db, client):
    """OWNER of business A cannot write to business B (cross-business IDOR)."""
    token, biz_a_id = _setup_owner(db, client)

    # Create business B in the same tenant directly (no membership for our user).
    biz_a = db.query(Business).filter(Business.id == biz_a_id).one()
    biz_b = Business(tenant_id=biz_a.tenant_id, name="Salon B", timezone="UTC", is_active=True)
    db.add(biz_b)
    db.commit()
    db.refresh(biz_b)

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/services",
        json=_create_service_payload(),
        headers=auth_headers(token),
    )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Platform admin bypass
# ---------------------------------------------------------------------------

def test_platform_admin_bypasses_membership_check(db, client):
    """platform_admin can write to any business without a membership row."""
    _, biz_id = _setup_owner(db, client)

    email = _email("platadmin")
    register_user(client, email)
    plat = db.query(User).filter(User.email == email).one()
    plat.role = "platform_admin"
    db.commit()
    plat_token = login_user(client, email).json()["access_token"]

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json=_create_service_payload(),
        headers=auth_headers(plat_token),
    )

    assert resp.status_code == 201
