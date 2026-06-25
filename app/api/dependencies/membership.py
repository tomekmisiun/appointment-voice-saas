"""Business membership FastAPI dependencies (SAC-005).

Provides `require_business_member(*roles)` for routes that have a
`{business_id}` path parameter. Platform admins bypass the membership
check (their cross-tenant access is governed by `User.role == "platform_admin"`
which is verified by `get_current_user` via the legacy permission system).
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.business_membership import MembershipRole
from app.models.user import User
from app.services.membership_service import assert_active_business_role


def require_business_member(*roles: MembershipRole):
    """Return a FastAPI dependency that enforces an active business membership.

    Inject as `current_user: User = Depends(require_business_member(OWNER, ADMIN))`.
    Raises 403 (via ForbiddenError → domain_error_handler) unless the
    authenticated user has an active membership in the path's `business_id`
    with one of the given roles, or is a platform_admin.
    """
    def checker(
        business_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role == "platform_admin":
            return current_user
        assert_active_business_role(db, current_user, business_id, *roles)
        return current_user

    return checker
