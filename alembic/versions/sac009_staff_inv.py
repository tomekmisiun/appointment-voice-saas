"""stub: sac009_staff_inv applied directly to production outside repo workflow

Revision ID: sac009_staff_inv
Revises: sac003a2b3c4d5e6
Create Date: 2026-06-27

BACKGROUND
----------
This revision was applied to the production database directly from an
unreleased contaminated branch (backup/mixed-work-before-recovery-2026-06-26,
see docs/archive/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md).  The original
migration created the staff_invitations table (SAC-009) with an HMAC token
column, partial unique index, and composite FK constraints.

This stub is intentionally a no-op so that:
  1. `alembic upgrade head` can locate the revision on production and continue
     to the next migration (demo_user_flag).
  2. Fresh databases do NOT get a staff_invitations table, consistent with the
     audit's ruling that SAC-009 must not be placed in the deployable chain
     until HTTP routes exist (see docs/archive/audits/…, finding F2 and section 8/6).

FUTURE IMPLEMENTATION NOTE
--------------------------
When SAC-009 is properly extracted onto its own branch, the real migration
MUST account for the fact that the staff_invitations table already exists on
the production database (it was created by the original sac009_staff_inv run).
Use `IF NOT EXISTS` guards or check for table existence before creating it.
"""

revision = "sac009_staff_inv"
down_revision = "sac003a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
