"""sac006_staff_profile_fields_and_audit_target_staff

Revision ID: a353d8c535c7
Revises: sac003a2b3c4d5e6
Create Date: 2026-06-25 17:14:04.436337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a353d8c535c7'
down_revision: Union[str, Sequence[str], None] = 'sac003a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SAC-006: staff profile fields + audit_logs.target_staff_id."""
    op.add_column('audit_logs', sa.Column('target_staff_id', sa.Integer(), nullable=True))
    op.create_index('ix_audit_logs_target_staff_id', 'audit_logs', ['target_staff_id'], unique=False)
    op.create_foreign_key(
        'audit_logs_target_staff_id_fkey', 'audit_logs', 'staff',
        ['target_staff_id'], ['id'],
    )

    op.add_column('staff', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('staff', sa.Column('position', sa.String(length=128), nullable=True))
    op.add_column('staff', sa.Column('accepts_bookings', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('staff', sa.Column('is_customer_visible', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('staff', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Reverse SAC-006 staff profile fields."""
    op.drop_column('staff', 'updated_at')
    op.drop_column('staff', 'is_customer_visible')
    op.drop_column('staff', 'accepts_bookings')
    op.drop_column('staff', 'position')
    op.drop_column('staff', 'contact_email')

    op.drop_constraint('audit_logs_target_staff_id_fkey', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_target_staff_id', table_name='audit_logs')
    op.drop_column('audit_logs', 'target_staff_id')
