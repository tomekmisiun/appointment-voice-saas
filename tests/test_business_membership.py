"""Tests for the business membership model (SAC-003, ADR 0007)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.business_membership import (
    BusinessMembership,
    MembershipRole,
    MembershipStatus,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.services.business_service import create_business
from app.services.staff_service import create_staff


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(db, tenant_id=tenant.id, name="Membership Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=business.id, name="Ola")
    return tenant.id, business.id, staff.id


def _create_user(db, tenant_id: int, email: str) -> User:
    user = User(
        tenant_id=tenant_id,
        email=email,
        hashed_password="hashed-password",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_owner_membership_persists_without_staff_link(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "owner-persist@example.com")

    membership = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user.id,
        role=MembershipRole.OWNER,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    assert membership.id is not None
    assert membership.staff_id is None
    assert membership.status == MembershipStatus.ACTIVE
    assert membership.created_at is not None
    assert membership.updated_at is not None


def test_staff_membership_requires_staff_link(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "staff-no-link@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.STAFF,
            staff_id=None,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_staff_membership_persists_with_staff_link(db):
    tenant_id, business_id, staff_id = _setup(db)
    user = _create_user(db, tenant_id, "staff-linked@example.com")

    membership = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user.id,
        role=MembershipRole.STAFF,
        staff_id=staff_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    assert membership.staff_id == staff_id


def test_rejects_duplicate_user_business_membership(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "dup-user@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id, business_id=business_id, user_id=user.id, role=MembershipRole.ADMIN
        )
    )
    db.commit()

    db.add(
        BusinessMembership(
            tenant_id=tenant_id, business_id=business_id, user_id=user.id, role=MembershipRole.ADMIN
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_second_active_membership_for_same_staff_link(db):
    tenant_id, business_id, staff_id = _setup(db)
    user_a = _create_user(db, tenant_id, "staff-active-a@example.com")
    user_b = _create_user(db, tenant_id, "staff-active-b@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user_a.id,
            role=MembershipRole.STAFF,
            staff_id=staff_id,
            status=MembershipStatus.ACTIVE,
        )
    )
    db.commit()

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user_b.id,
            role=MembershipRole.STAFF,
            staff_id=staff_id,
            status=MembershipStatus.ACTIVE,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_revoked_staff_membership_does_not_block_new_active_one(db):
    tenant_id, business_id, staff_id = _setup(db)
    user_a = _create_user(db, tenant_id, "staff-revoked-a@example.com")
    user_b = _create_user(db, tenant_id, "staff-revoked-b@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user_a.id,
            role=MembershipRole.STAFF,
            staff_id=staff_id,
            status=MembershipStatus.REVOKED,
        )
    )
    db.commit()

    new_membership = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user_b.id,
        role=MembershipRole.STAFF,
        staff_id=staff_id,
        status=MembershipStatus.ACTIVE,
    )
    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    assert new_membership.id is not None


def test_deleting_membership_does_not_delete_linked_staff(db):
    tenant_id, business_id, staff_id = _setup(db)
    user = _create_user(db, tenant_id, "delete-membership@example.com")

    membership = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user.id,
        role=MembershipRole.STAFF,
        staff_id=staff_id,
    )
    db.add(membership)
    db.commit()

    db.delete(membership)
    db.commit()

    from app.models.staff import Staff

    assert db.query(Staff).filter(Staff.id == staff_id).first() is not None


def test_query_scoped_to_tenant_excludes_other_tenant_memberships(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "tenant-scope@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id, business_id=business_id, user_id=user.id, role=MembershipRole.OWNER
        )
    )
    db.commit()

    other_tenant = Tenant(slug="membership-other", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)

    results = (
        db.query(BusinessMembership)
        .filter(BusinessMembership.tenant_id == other_tenant.id)
        .all()
    )
    assert results == []


def test_rejects_business_from_a_different_tenant(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "cross-tenant-business@example.com")

    other_tenant = Tenant(slug="membership-cross-a", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)

    db.add(
        BusinessMembership(
            tenant_id=other_tenant.id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.OWNER,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_user_from_a_different_tenant(db):
    tenant_id, business_id, _staff_id = _setup(db)

    other_tenant = Tenant(slug="membership-cross-b", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)
    other_user = _create_user(db, other_tenant.id, "cross-tenant-user@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=other_user.id,
            role=MembershipRole.OWNER,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_invalid_role_value(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "invalid-role@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id, business_id=business_id, user_id=user.id, role="root"
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_invalid_status_value(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "invalid-status@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.OWNER,
            status="deleted",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_invited_by_user_from_a_different_tenant(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "invited-by-target@example.com")

    other_tenant = Tenant(slug="membership-cross-c", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)
    other_user = _create_user(db, other_tenant.id, "invited-by-actor@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.OWNER,
            invited_by_user_id=other_user.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_revoked_by_user_from_a_different_tenant(db):
    tenant_id, business_id, _staff_id = _setup(db)
    user = _create_user(db, tenant_id, "revoked-by-target@example.com")

    other_tenant = Tenant(slug="membership-cross-d", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)
    other_user = _create_user(db, other_tenant.id, "revoked-by-actor@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.OWNER,
            status=MembershipStatus.REVOKED,
            revoked_by_user_id=other_user.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_rejects_staff_from_a_different_business(db):
    tenant_id, business_id, _staff_id = _setup(db)
    other_business = create_business(
        db, tenant_id=tenant_id, name="Other Business", timezone="UTC"
    )
    other_staff = create_staff(
        db, tenant_id=tenant_id, business_id=other_business.id, name="Other Staffer"
    )
    user = _create_user(db, tenant_id, "cross-business-staff@example.com")

    db.add(
        BusinessMembership(
            tenant_id=tenant_id,
            business_id=business_id,
            user_id=user.id,
            role=MembershipRole.STAFF,
            staff_id=other_staff.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
