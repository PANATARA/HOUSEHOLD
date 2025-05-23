"""comment

Revision ID: 35462464481e
Revises: 567a9bed8181
Create Date: 2025-05-02 19:17:38.496294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35462464481e'
down_revision: Union[str, None] = '567a9bed8181'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users_family_permissions', 'can_invite_users',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users_family_permissions', 'can_invite_users',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    # ### end Alembic commands ###
