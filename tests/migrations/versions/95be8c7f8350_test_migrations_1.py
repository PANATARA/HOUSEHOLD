"""initial migration

Revision ID: 95be8c7f8350
Revises: 
Create Date: 2025-04-13 11:25:15.946190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '95be8c7f8350'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'family',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('icon', sa.String(), nullable=False),
        sa.Column('family_admin_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=60), unique=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('surname', sa.String(length=50), nullable=True),
        sa.Column('family_id', sa.UUID(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='SET NULL')
    )

    op.create_foreign_key(None, 'family', 'users', ['family_admin_id'], ['id'], ondelete='SET NULL')

    op.create_table(
        'chores',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('icon', sa.String(), nullable=False),
        sa.Column('valuation', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL')
    )

    op.create_table(
        'products',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('icon', sa.String(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('seller_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='SET NULL')
    )

    op.create_table(
        'users_family_permissions',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), unique=True, nullable=False),
        sa.Column('should_confirm_chore_completion', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    op.create_table(
        'users_settings',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), unique=True, nullable=False),
        sa.Column('app_theme', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    op.create_table(
        'wallets',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.UUID(), unique=True, nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_reward_transactions_to_user_id'), table_name='reward_transactions')
    op.drop_index(op.f('ix_reward_transactions_chore_completion_id'), table_name='reward_transactions')
    op.drop_table('reward_transactions')
    op.drop_table('chore_confirmation')
    op.drop_table('product_buyers')
    op.drop_index(op.f('ix_peer_transactions_to_user_id'), table_name='peer_transactions')
    op.drop_index(op.f('ix_peer_transactions_product_id'), table_name='peer_transactions')
    op.drop_index(op.f('ix_peer_transactions_from_user_id'), table_name='peer_transactions')
    op.drop_table('peer_transactions')
    op.drop_table('chore_completion')
    op.drop_table('wallets')
    op.drop_table('users_settings')
    op.drop_table('users_family_permissions')
    op.drop_table('products')
    op.drop_table('chores')
    op.drop_table('users')
    op.drop_table('family')
    # ### end Alembic commands ###
