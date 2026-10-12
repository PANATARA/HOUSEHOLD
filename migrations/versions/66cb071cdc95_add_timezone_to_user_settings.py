"""add_timezone_to_user_settings

Revision ID: 66cb071cdc95
Revises: 611021d58456
Create Date: 2026-10-12 14:49:54.345515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66cb071cdc95'
down_revision: Union[str, None] = '611021d58456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users_settings',
        sa.Column('timezone', sa.String(length=50), server_default='UTC', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users_settings', 'timezone')

