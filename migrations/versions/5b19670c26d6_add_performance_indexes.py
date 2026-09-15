"""Add performance indexes for high-frequency queries and foreign keys

Revision ID: 5b19670c26d6
Revises: d891e48f12a0
Create Date: 2026-09-15 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5b19670c26d6'
down_revision: Union[str, None] = 'd891e48f12a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. USERS & FAMILY ─────────────────────────────────────────
    op.create_index('ix_users_family_id', 'users', ['family_id'], unique=False)
    op.create_index('ix_family_family_admin_id', 'family', ['family_admin_id'], unique=False)
    op.create_index('ix_events_family_id_date', 'events', ['family_id', 'date'], unique=False)

    # ─── 2. CHORES & DEFAULT CHORES ────────────────────────────────
    op.create_index('ix_chores_family_id_is_active', 'chores', ['family_id', 'is_active'], unique=False)
    op.create_index('ix_chores_default_chore_id', 'chores', ['default_chore_id'], unique=False)
    op.create_index('ix_default_chore_is_active_order', 'default_chore', ['is_active', 'order'], unique=False)
    op.create_index('ix_default_chore_trans_chore_id_lang', 'default_chore_translation', ['default_chore_id', 'language'], unique=False)

    # ─── 3. PLANNED CHORES & SCHEDULES ─────────────────────────────
    op.create_index('ix_planned_chore_family_active_due', 'planned_chore', ['family_id', 'is_active', 'due_date'], unique=False)
    op.create_index('ix_planned_chore_family_completed_due', 'planned_chore', ['family_id', 'completed_by_id', 'due_date'], unique=False)
    op.create_index('ix_planned_chore_completed_due', 'planned_chore', ['completed_by_id', 'due_date'], unique=False)
    op.create_index('ix_planned_chore_schedule_due', 'planned_chore', ['schedule_id', 'due_date'], unique=False)
    op.create_index('ix_planned_chore_assigned_to_id', 'planned_chore', ['assigned_to_id'], unique=False)
    op.create_index('ix_planned_chore_chore_id', 'planned_chore', ['chore_id'], unique=False)

    op.create_index('ix_chore_schedule_family_is_active', 'chore_schedule', ['family_id', 'is_active'], unique=False)
    op.create_index('ix_chore_schedule_chore_is_active', 'chore_schedule', ['chore_id', 'is_active'], unique=False)

    op.create_index('ix_quick_planned_chore_family_active_due', 'quick_planned_chore', ['family_id', 'is_active', 'due_date'], unique=False)
    op.create_index('ix_quick_planned_chore_completed_by_id', 'quick_planned_chore', ['completed_by_id'], unique=False)
    op.create_index('ix_quick_planned_chore_assigned_to_id', 'quick_planned_chore', ['assigned_to_id'], unique=False)

    # ─── 4. MEALS & RECIPES ────────────────────────────────────────
    op.create_index('ix_recipes_family_id_is_active', 'recipes', ['family_id', 'is_active'], unique=False)
    op.create_index('ix_recipes_created_by_id', 'recipes', ['created_by_id'], unique=False)

    op.create_index('ix_planned_meals_family_date_active', 'planned_meals', ['family_id', 'date', 'is_active'], unique=False)
    op.create_index('ix_planned_meals_recipe_id', 'planned_meals', ['recipe_id'], unique=False)
    op.create_index('ix_planned_meals_assigned_cook_id', 'planned_meals', ['assigned_cook_id'], unique=False)
    op.create_index('ix_planned_meals_completed_by_id', 'planned_meals', ['completed_by_id'], unique=False)

    op.create_index('ix_grocery_items_family_active_bought', 'grocery_items', ['family_id', 'is_active', 'is_bought'], unique=False)

    # ─── 5. PRODUCTS ───────────────────────────────────────────────
    op.create_index('ix_products_family_id_is_active', 'products', ['family_id', 'is_active'], unique=False)
    op.create_index('ix_products_seller_id_is_active', 'products', ['seller_id', 'is_active'], unique=False)

    # ─── 6. TRANSACTIONS ───────────────────────────────────────────
    op.create_index('ix_peer_transactions_to_user_created', 'peer_transactions', ['to_user_id', 'created_at'], unique=False)
    op.create_index('ix_peer_transactions_from_user_created', 'peer_transactions', ['from_user_id', 'created_at'], unique=False)
    op.create_index('ix_reward_transactions_to_user_created', 'reward_transactions', ['to_user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # ─── 6. TRANSACTIONS ───────────────────────────────────────────
    op.drop_index('ix_reward_transactions_to_user_created', table_name='reward_transactions')
    op.drop_index('ix_peer_transactions_from_user_created', table_name='peer_transactions')
    op.drop_index('ix_peer_transactions_to_user_created', table_name='peer_transactions')

    # ─── 5. PRODUCTS ───────────────────────────────────────────────
    op.drop_index('ix_products_seller_id_is_active', table_name='products')
    op.drop_index('ix_products_family_id_is_active', table_name='products')

    # ─── 4. MEALS & RECIPES ────────────────────────────────────────
    op.drop_index('ix_grocery_items_family_active_bought', table_name='grocery_items')
    op.drop_index('ix_planned_meals_completed_by_id', table_name='planned_meals')
    op.drop_index('ix_planned_meals_assigned_cook_id', table_name='planned_meals')
    op.drop_index('ix_planned_meals_recipe_id', table_name='planned_meals')
    op.drop_index('ix_planned_meals_family_date_active', table_name='planned_meals')
    op.drop_index('ix_recipes_created_by_id', table_name='recipes')
    op.drop_index('ix_recipes_family_id_is_active', table_name='recipes')

    # ─── 3. PLANNED CHORES & SCHEDULES ─────────────────────────────
    op.drop_index('ix_quick_planned_chore_assigned_to_id', table_name='quick_planned_chore')
    op.drop_index('ix_quick_planned_chore_completed_by_id', table_name='quick_planned_chore')
    op.drop_index('ix_quick_planned_chore_family_active_due', table_name='quick_planned_chore')

    op.drop_index('ix_chore_schedule_chore_is_active', table_name='chore_schedule')
    op.drop_index('ix_chore_schedule_family_is_active', table_name='chore_schedule')

    op.drop_index('ix_planned_chore_chore_id', table_name='planned_chore')
    op.drop_index('ix_planned_chore_assigned_to_id', table_name='planned_chore')
    op.drop_index('ix_planned_chore_schedule_due', table_name='planned_chore')
    op.drop_index('ix_planned_chore_completed_due', table_name='planned_chore')
    op.drop_index('ix_planned_chore_family_completed_due', table_name='planned_chore')
    op.drop_index('ix_planned_chore_family_active_due', table_name='planned_chore')

    # ─── 2. CHORES & DEFAULT CHORES ────────────────────────────────
    op.drop_index('ix_default_chore_trans_chore_id_lang', table_name='default_chore_translation')
    op.drop_index('ix_default_chore_is_active_order', table_name='default_chore')
    op.drop_index('ix_chores_default_chore_id', table_name='chores')
    op.drop_index('ix_chores_family_id_is_active', table_name='chores')

    # ─── 1. USERS & FAMILY ─────────────────────────────────────────
    op.drop_index('ix_events_family_id_date', table_name='events')
    op.drop_index('ix_family_family_admin_id', table_name='family')
    op.drop_index('ix_users_family_id', table_name='users')
