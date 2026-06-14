"""add no-overlap exclusion constraint on bookings

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-06-14 13:00:00.000000

Prevents double-booking the same staff member at the same time at the DB level.
Requires the btree_gist PostgreSQL extension (included in postgres-contrib).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT no_overlapping_staff_bookings
        EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status = 'confirmed' AND staff_id IS NOT NULL)
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE bookings DROP CONSTRAINT no_overlapping_staff_bookings"
    )
