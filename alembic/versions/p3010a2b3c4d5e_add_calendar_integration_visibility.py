"""add CalendarIntegration.visibility for private/public outbound sync
(P3-010, ADR 0005/0006 follow-up)

Revision ID: p3010a2b3c4d5e
Revises: p3008a2b3c4d5e
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "p3010a2b3c4d5e"
down_revision = "p3008a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_integrations",
        sa.Column(
            "visibility",
            sa.String(length=16),
            nullable=False,
            server_default="public",
        ),
    )


def downgrade() -> None:
    op.drop_column("calendar_integrations", "visibility")
