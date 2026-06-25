"""SAC-006: Staff profile lifecycle and history safety tests."""

from app.models.audit_log import AuditAction
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit_log_service import get_audit_logs
from app.services.booking_service import create_booking, cancel_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import (
    create_staff,
    deactivate_staff,
    get_eligible_transfer_staff,
    list_staff,
    reactivate_staff,
    require_staff_in_business,
)
from datetime import datetime, timezone
from tests.database import auth_headers, login_user, promote_to_admin, register_user


_FUTURE = datetime(2028, 3, 10, 10, 0, tzinfo=timezone.utc)


def _admin_with_business(db, client, email: str) -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "Salon", "timezone": "UTC"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def _give_membership(db, email: str, biz) -> None:
    user = db.query(User).filter(User.email == email).one()
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz.id,
        user_id=user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# Profile fields
# ---------------------------------------------------------------------------

def test_create_staff_with_full_profile(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-create@example.com")

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={
            "name": "Ola",
            "phone": "+48600111222",
            "contact_email": "ola@salon.pl",
            "position": "Senior Stylist",
            "accepts_bookings": True,
            "is_customer_visible": False,
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ola"
    assert data["contact_email"] == "ola@salon.pl"
    assert data["position"] == "Senior Stylist"
    assert data["accepts_bookings"] is True
    assert data["is_customer_visible"] is False
    assert data["is_active"] is True
    assert data["updated_at"] is None


def test_update_staff_profile_fields(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-update@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Marek"},
        headers=auth_headers(token),
    ).json()

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}",
        json={"position": "Junior Barber", "accepts_bookings": False},
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["position"] == "Junior Barber"
    assert data["accepts_bookings"] is False
    assert data["name"] == "Marek"


# ---------------------------------------------------------------------------
# Deactivate / reactivate endpoints
# ---------------------------------------------------------------------------

def test_deactivate_staff_api(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-deact@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Tomek"},
        headers=auth_headers(token),
    ).json()

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/deactivate",
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_reactivate_staff_api(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-react@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Zosia"},
        headers=auth_headers(token),
    ).json()
    client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/deactivate",
        headers=auth_headers(token),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/reactivate",
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_deactivated_staff_not_in_default_list(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-hide@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Hidden"},
        headers=auth_headers(token),
    ).json()
    client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/deactivate",
        headers=auth_headers(token),
    )

    active_list = client.get(
        f"/api/v1/businesses/{biz_id}/staff",
        headers=auth_headers(token),
    ).json()
    all_list = client.get(
        f"/api/v1/businesses/{biz_id}/staff?include_inactive=true",
        headers=auth_headers(token),
    ).json()

    assert not any(s["id"] == staff["id"] for s in active_list)
    assert any(s["id"] == staff["id"] for s in all_list)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def test_deactivate_emits_audit_log(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-audit-deact@example.com")
    actor = db.query(User).filter(User.email == "sac6-audit-deact@example.com").one()
    tenant = db.query(Tenant).filter(Tenant.id == actor.tenant_id).one()
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Pawel"},
        headers=auth_headers(token),
    ).json()

    client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/deactivate",
        headers=auth_headers(token),
    )

    logs = get_audit_logs(db, tenant.id)
    entry = next(
        (l for l in logs if l.action == AuditAction.STAFF_DEACTIVATED and l.target_staff_id == staff["id"]),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id


def test_reactivate_emits_audit_log(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-audit-react@example.com")
    actor = db.query(User).filter(User.email == "sac6-audit-react@example.com").one()
    tenant = db.query(Tenant).filter(Tenant.id == actor.tenant_id).one()
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Basia"},
        headers=auth_headers(token),
    ).json()
    client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/deactivate",
        headers=auth_headers(token),
    )

    client.post(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}/reactivate",
        headers=auth_headers(token),
    )

    logs = get_audit_logs(db, tenant.id)
    entry = next(
        (l for l in logs if l.action == AuditAction.STAFF_REACTIVATED and l.target_staff_id == staff["id"]),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id


# ---------------------------------------------------------------------------
# History safety
# ---------------------------------------------------------------------------

def test_deactivated_staff_bookings_still_readable(db):
    """Deactivating a staff member must not remove or hide their past bookings."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="History Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Jola")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48611222333")

    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_FUTURE,
    )

    actor = db.query(User).filter(User.tenant_id == tenant.id).first()
    deactivate_staff(db, staff.id, biz.id, tenant.id, actor_id=actor.id)

    # Staff row still exists (soft delete only)
    still_there = require_staff_in_business(db, staff.id, biz.id, tenant.id)
    assert still_there.is_active is False
    assert still_there.id == staff.id

    # Booking still references the deactivated staff
    db.refresh(booking)
    assert booking.staff_id == staff.id


def test_deactivated_staff_visible_via_include_inactive(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Visible Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Wacek")
    actor = db.query(User).filter(User.tenant_id == tenant.id).first()

    deactivate_staff(db, staff.id, biz.id, tenant.id, actor_id=actor.id)

    active_only = list_staff(db, biz.id, tenant.id)
    with_inactive = list_staff(db, biz.id, tenant.id, include_inactive=True)

    assert not any(s.id == staff.id for s in active_only)
    assert any(s.id == staff.id for s in with_inactive)


# ---------------------------------------------------------------------------
# accepts_bookings flag — affects transfer staff eligibility
# ---------------------------------------------------------------------------

def test_patch_clears_nullable_profile_fields(db, client):
    """PATCH with explicit null must clear a nullable field, not silently skip it."""
    token, biz_id = _admin_with_business(db, client, "sac6-clear@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Ewa", "position": "Head Stylist"},
        headers=auth_headers(token),
    ).json()
    assert staff["position"] == "Head Stylist"

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}",
        json={"position": None},
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    assert resp.json()["position"] is None


def test_patch_is_active_false_deactivates_with_audit(db, client):
    """PATCH is_active:false must route through deactivate_staff for backward compat."""
    token, biz_id = _admin_with_business(db, client, "sac6-compat@example.com")
    actor = db.query(User).filter(User.email == "sac6-compat@example.com").one()
    tenant = db.query(Tenant).filter(Tenant.id == actor.tenant_id).one()
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Zbyszek"},
        headers=auth_headers(token),
    ).json()

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    logs = get_audit_logs(db, tenant.id)
    entry = next(
        (l for l in logs if l.action == AuditAction.STAFF_DEACTIVATED and l.target_staff_id == staff["id"]),
        None,
    )
    assert entry is not None


def test_accepts_bookings_false_excludes_from_transfer_staff(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Transfer Salon", timezone="UTC")

    bookable = create_staff(
        db, tenant_id=tenant.id, business_id=biz.id,
        name="Bookable", phone="+48600010001",
        accepts_bookings=True,
    )
    not_bookable = create_staff(
        db, tenant_id=tenant.id, business_id=biz.id,
        name="NotBookable", phone="+48600020002",
        accepts_bookings=False,
    )

    eligible = get_eligible_transfer_staff(db, biz.id, tenant.id)

    assert any(s.id == bookable.id for s in eligible)
    assert not any(s.id == not_bookable.id for s in eligible)


# ---------------------------------------------------------------------------
# Permissions: STAFF role cannot deactivate
# ---------------------------------------------------------------------------

def test_staff_role_cannot_deactivate(db, client):
    token, biz_id = _admin_with_business(db, client, "sac6-perm-owner@example.com")

    # Create a user with STAFF membership
    register_user(client, "sac6-perm-staff@example.com")
    staff_user = db.query(User).filter(User.email == "sac6-perm-staff@example.com").one()
    from app.models.staff import Staff as StaffModel
    staff_record = StaffModel(
        tenant_id=staff_user.tenant_id,
        business_id=biz_id,
        name="Worker",
        is_active=True,
    )
    db.add(staff_record)
    db.flush()
    db.add(BusinessMembership(
        tenant_id=staff_user.tenant_id,
        business_id=biz_id,
        user_id=staff_user.id,
        staff_id=staff_record.id,
        role=MembershipRole.STAFF,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()
    staff_token = login_user(client, "sac6-perm-staff@example.com").json()["access_token"]

    # Create a target staff member to try to deactivate
    target = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Target"},
        headers=auth_headers(token),
    ).json()

    resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff/{target['id']}/deactivate",
        headers=auth_headers(staff_token),
    )

    assert resp.status_code == 403
