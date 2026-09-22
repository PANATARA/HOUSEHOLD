"""Add user_devices table for push notifications

Revision ID: e8d25b1c94a2
Revises: 5b19670c26d6
Create Date: 2026-09-22 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d25b1c94a2'
down_revision: Union[str, None] = '5b19670c26d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_devices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('device_type', sa.String(length=50), server_default='android', nullable=False),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_devices_token', 'user_devices', ['token'], unique=True)
    op.create_index('ix_user_devices_user_id', 'user_devices', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_devices_user_id', table_name='user_devices')
    op.drop_index('ix_user_devices_token', table_name='user_devices')
    op.drop_table('user_devices')
