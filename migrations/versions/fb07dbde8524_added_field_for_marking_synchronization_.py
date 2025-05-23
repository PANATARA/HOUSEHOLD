"""added field for marking synchronization chore_completion

Revision ID: fb07dbde8524
Revises: 625e15194853
Create Date: 2025-04-22 19:18:10.582572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb07dbde8524'
down_revision: Union[str, None] = '625e15194853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chore_completion', sa.Column('synced_to_ch', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('chore_completion', 'synced_to_ch')
    # ### end Alembic commands ###
