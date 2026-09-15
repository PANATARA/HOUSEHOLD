"""Add models for Meals, Recipes, Planner, and Grocery Items

Revision ID: d891e48f12a0
Revises: c4783f44080d
Create Date: 2026-09-11 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd891e48f12a0'
down_revision: Union[str, None] = 'c4783f44080d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. RECIPES TABLE ──────────────────────────────────────────
    op.create_table(
        'recipes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=1024), nullable=True),
        sa.Column('prep_time_minutes', sa.Integer(), server_default='10', nullable=False),
        sa.Column('cook_time_minutes', sa.Integer(), server_default='20', nullable=False),
        sa.Column('base_servings', sa.Integer(), server_default='4', nullable=False),
        sa.Column('category', sa.String(length=50), server_default='quick', nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_custom', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('accent_gradient', sa.String(length=200), server_default='linear-gradient(135deg, #F97316 0%, #EA580C 100%)', nullable=False),
        sa.Column('emoji', sa.String(length=16), server_default='🍲', nullable=False),
        sa.Column('ingredients', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # ─── 2. PLANNED MEALS TABLE ────────────────────────────────────
    op.create_table(
        'planned_meals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('slot', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('prep_time_minutes', sa.Integer(), server_default='15', nullable=False),
        sa.Column('recipe_id', sa.UUID(), nullable=True),
        sa.Column('assigned_cook_id', sa.UUID(), nullable=True),
        sa.Column('servings', sa.Integer(), server_default='4', nullable=False),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('is_completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('completed_by_id', sa.UUID(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_cook_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # ─── 3. GROCERY ITEMS TABLE ────────────────────────────────────
    op.create_table(
        'grocery_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=30), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_bought', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('added_from_recipe', sa.String(length=128), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['family.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('grocery_items')
    op.drop_table('planned_meals')
    op.drop_table('recipes')
