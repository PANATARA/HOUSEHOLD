"""add_unique_constraint_to_default_chore_translation

Revision ID: 59e4b3ea9126
Revises: 66cb071cdc95
Create Date: 2026-10-12 15:25:00.425997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59e4b3ea9126'
down_revision: Union[str, None] = '66cb071cdc95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_default_chore_translation_chore_lang',
        'default_chore_translation',
        ['default_chore_id', 'language'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_default_chore_translation_chore_lang',
        'default_chore_translation',
        type_='unique',
    )

