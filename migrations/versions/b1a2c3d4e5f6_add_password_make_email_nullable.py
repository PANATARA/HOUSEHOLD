"""Add hashed_password and make email nullable

Revision ID: b1a2c3d4e5f6
Revises: b92c4f7a1d8e
Create Date: 2026-09-23 03:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'b92c4f7a1d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=False)
    op.drop_column('users', 'hashed_password')
