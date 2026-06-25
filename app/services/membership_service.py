"""Business membership RBAC helpers (SAC-005).

Provides the service-layer primitives for SAC-005 membership authorization:
lookup, role assertion, and status mutation (suspend/revoke) with automatic
session invalidation.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.domain_errors import ForbiddenError
from app.models.business_membership import (
    BusinessMembership,
    MembershipRole,
    MembershipStatus,
)
from app.models.user import User
from app.services.user_service import increment_user_token_version


def get_active_business_membership(
    db: Session,
    *,
    user_id: int,
    business_id: int,
    tenant_id: int,
) -> BusinessMembership | None:
    return (
        db.query(BusinessMembership)
        .filter(
            BusinessMembership.user_id == user_id,
            BusinessMembership.business_id == business_id,
            BusinessMembership.tenant_id == tenant_id,
            BusinessMembership.status == MembershipStatus.ACTIVE,
        )
        .first()
    )


def assert_active_business_role(
    db: Session,
    user: User,
    business_id: int,
    *roles: MembershipRole,
) -> BusinessMembership:
    """Raise ForbiddenError unless the user has an active membership in
    business_id with one of the given roles. Used by both the FastAPI
    dependency layer and internal service assertions."""
    membership = get_active_business_membership(
        db, user_id=user.id, business_id=business_id, tenant_id=user.tenant_id
    )
    if membership is None or MembershipRole(membership.role) not in roles:
        raise ForbiddenError("Insufficient business membership")
    return membership


def create_owner_membership(
    db: Session,
    *,
    user_id: int,
    business_id: int,
    tenant_id: int,
) -> BusinessMembership:
    """Create an OWNER membership for a user who just created a business.
    Callers must ensure no membership of ANY status exists for this
    (business_id, user_id) pair — the unique index covers all statuses."""
    membership = BusinessMembership(
        tenant_id=tenant_id,
        business_id=business_id,
        user_id=user_id,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.flush()
    return membership


def revoke_membership(
    db: Session,
    membership: BusinessMembership,
    revoked_by_user_id: int,
) -> BusinessMembership:
    """Revoke a membership and invalidate the member's active sessions."""
    user = db.query(User).filter(User.id == membership.user_id).one()
    membership.status = MembershipStatus.REVOKED
    membership.revoked_at = datetime.now(timezone.utc)
    membership.revoked_by_user_id = revoked_by_user_id
    increment_user_token_version(db, user)
    db.flush()
    return membership


def suspend_membership(db: Session, membership: BusinessMembership) -> BusinessMembership:
    """Suspend a membership and invalidate the member's active sessions."""
    user = db.query(User).filter(User.id == membership.user_id).one()
    membership.status = MembershipStatus.SUSPENDED
    increment_user_token_version(db, user)
    db.flush()
    return membership
