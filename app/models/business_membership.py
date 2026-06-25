from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class MembershipRole(StrEnum):
    """docs/specs/staff-access-and-calendar.md `business_memberships` (SAC-003)."""
    OWNER = "owner"
    ADMIN = "admin"
    STAFF = "staff"


class MembershipStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class BusinessMembership(Base):
    """User access to one tenant/business (ADR 0007, SAC-003). Authorization
    is membership-based: a user's role/status here -- not `User.role` --
    is the target source of truth once SAC-005 makes it authoritative.
    SAC-002's migration runbook governs how legacy `User.tenant_id`/`role`
    and this table coexist until then.

    No ORM `relationship()` declarations to tenant/business/user/staff: this
    codebase resolves cross-model access via explicit queries rather than
    relationship traversal (the one exception, User/PasswordResetToken, is
    not the norm). The composite `ForeignKeyConstraint`s below are the
    relationship enforcement for this table -- they are DB-level, not ORM."""

    __tablename__ = "business_memberships"
    __table_args__ = (
        Index(
            "uix_business_memberships_business_user",
            "business_id",
            "user_id",
            unique=True,
        ),
        # Partial: only one *active* staff-linked membership per staff record.
        # A revoked/suspended/invited row for the same staff_id does not
        # block a new active one (e.g. re-inviting after revocation).
        Index(
            "uix_business_memberships_business_staff_active",
            "business_id",
            "staff_id",
            unique=True,
            postgresql_where=text("staff_id IS NOT NULL AND status = 'active'"),
        ),
        Index(
            "ix_business_memberships_tenant_business_status",
            "tenant_id",
            "business_id",
            "status",
        ),
        Index("ix_business_memberships_user_id", "user_id"),
        Index("ix_business_memberships_staff_id", "staff_id"),
        CheckConstraint(
            "role != 'staff' OR staff_id IS NOT NULL",
            name="ck_business_memberships_staff_role_requires_staff_id",
        ),
        CheckConstraint(
            "role IN ('owner', 'admin', 'staff')",
            name="ck_business_memberships_role_valid",
        ),
        CheckConstraint(
            "status IN ('invited', 'active', 'suspended', 'revoked')",
            name="ck_business_memberships_status_valid",
        ),
        # Composite FKs (not single-column) so the DB itself rejects a
        # membership whose business/user/staff belongs to a different
        # tenant/business than the membership row claims -- this is the
        # core authorization table, so cross-scope drift here is a critical
        # defect (.ai-rules/tenancy.md), not just a data-hygiene nit. Each
        # target needs a matching unique index on the referenced table
        # (added alongside this migration): businesses(tenant_id, id),
        # users(tenant_id, id), staff(business_id, id). A NULL staff_id
        # is not checked by its composite FK (Postgres MATCH SIMPLE
        # default), so owner/admin memberships without a staff link are
        # unaffected.
        ForeignKeyConstraint(
            ["tenant_id", "business_id"],
            ["businesses.tenant_id", "businesses.id"],
            name="fk_business_memberships_business_same_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_user_same_tenant",
        ),
        ForeignKeyConstraint(
            ["business_id", "staff_id"],
            ["staff.business_id", "staff.id"],
            name="fk_business_memberships_staff_same_business",
        ),
        # invited_by_user_id/revoked_by_user_id are actors recorded on this
        # authorization table, so they get the same tenant-scoped composite
        # FK treatment as user_id -- otherwise the DB would let an
        # invite/revoke be attributed to a user from a different tenant.
        ForeignKeyConstraint(
            ["tenant_id", "invited_by_user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_invited_by_same_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "revoked_by_user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_revoked_by_same_tenant",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # tenant_id is also covered transitively by the composite FKs below (it
    # must match the tenant_id on the referenced business and user rows),
    # but keeps its own direct FK for clarity and consistency with every
    # other tenant-scoped model in this codebase.
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    staff_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=MembershipStatus.ACTIVE
    )
    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # FK is the composite (tenant_id, *_by_user_id) constraint above, not a
    # single-column FK, so the actor is tenant-scope checked like user_id.
    invited_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revoked_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
