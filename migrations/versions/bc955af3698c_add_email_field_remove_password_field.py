"""add email field, remove password field

Revision ID: bc955af3698c
Revises: a03ea45cb10d
Create Date: 2025-06-24 22:06:07.434597

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = "bc955af3698c"
down_revision: Union[str, None] = "a03ea45cb10d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))

    conn = op.get_bind()
    users_table = table(
        "users",
        column("id", sa.Integer),
        column("email", sa.String),
    )

    result = conn.execute(sa.text("SELECT id FROM users"))
    for idx, row in enumerate(result.fetchall(), start=1):
        fake_email = f"user{row.id}@example.com"
        conn.execute(
            users_table.update()
            .where(users_table.c.id == row.id)
            .values(email=fake_email)
        )

    op.alter_column("users", "email", nullable=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.drop_column("users", "password")
    op.alter_column("users", "name", existing_type=sa.VARCHAR(length=50), nullable=True)


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.alter_column(
        "users", "name", existing_type=sa.VARCHAR(length=50), nullable=False
    )
    op.drop_column("users", "email")
    # ### end Alembic commands ###
