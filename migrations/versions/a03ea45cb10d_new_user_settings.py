"""new user settings

Revision ID: a03ea45cb10d
Revises: 09910561ae1a
Create Date: 2025-05-02 20:27:00.759251

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a03ea45cb10d'
down_revision: Union[str, None] = '09910561ae1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users_settings', sa.Column('language', sa.String(), nullable=True))
    op.add_column('users_settings', sa.Column('date_of_birth', sa.Date(), nullable=True))

    op.execute("UPDATE users_settings SET language = 'ru' WHERE language IS NULL")
    op.execute("UPDATE users_settings SET date_of_birth = '2001-01-01' WHERE date_of_birth IS NULL")

    op.alter_column('users_settings', 'language', nullable=False)
    op.alter_column('users_settings', 'date_of_birth', nullable=False)

def downgrade() -> None:
    op.drop_column('users_settings', 'date_of_birth')
    op.drop_column('users_settings', 'language')
