"""
Integration tests for Meal and Grocery services:
- PlannedMealCreatorService
- PlannedMealUpdateService
- PlannedMealToggleService
- GroceryItemCreatorService
- GroceryBatchAddService
- GroceryItemRepository.toggle_bought_status
"""

import datetime
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meals.models import GroceryItem, PlannedMeal
from meals.repository import GroceryItemRepository, PlannedMealRepository
from meals.schemas import (
    GroceryBatchAddSchema,
    GroceryItemCreateSchema,
    PlannedMealCreateSchema,
    PlannedMealUpdateSchema,
)
from meals.services import (
    GroceryBatchAddService,
    GroceryItemCreatorService,
    PlannedMealCreatorService,
    PlannedMealToggleService,
    PlannedMealUpdateService,
)


class TestPlannedMealServices:
    """Integration tests for PlannedMeal service operations."""

    async def test_create_planned_meal_without_recipe(
        self, db_session: AsyncSession, integration_factory
    ):
        today = datetime.date.today()
        data = PlannedMealCreateSchema(
            date=today,
            slot="breakfast",
            title="Pancakes with Maple Syrup",
            prep_time_minutes=25,
            servings=4,
            note="Use gluten-free flour",
        )
        svc = PlannedMealCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        meal = await svc.run_process()

        assert meal.id is not None
        assert meal.title == "Pancakes with Maple Syrup"
        assert meal.slot == "breakfast"
        assert meal.servings == 4
        assert meal.note == "Use gluten-free flour"
        assert meal.is_completed is False
        assert meal.family_id == integration_factory.family.id

    async def test_create_planned_meal_with_recipe_and_assigned_cook(
        self, db_session: AsyncSession, integration_factory
    ):
        recipe = await integration_factory.create_recipe("Classic Lasagna")
        today = datetime.date.today()

        data = PlannedMealCreateSchema(
            date=today,
            slot="dinner",
            title=recipe.title,
            recipe_id=recipe.id,
            assigned_cook_id=integration_factory.user2.id,
            servings=6,
        )
        svc = PlannedMealCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        meal = await svc.run_process()

        assert meal.recipe_id == recipe.id
        assert meal.assigned_cook_id == integration_factory.user2.id
        assert meal.cook is not None
        assert meal.cook.id == integration_factory.user2.id

    async def test_update_planned_meal_fields(
        self, db_session: AsyncSession, integration_factory
    ):
        meal = await integration_factory.create_planned_meal(slot="lunch", title="Sandwich")

        update_data = PlannedMealUpdateSchema(
            title="Gourmet Club Sandwich",
            servings=2,
            note="Extra mustard",
        )
        svc = PlannedMealUpdateService(
            meal=meal,
            data=update_data,
            db_session=db_session,
        )
        updated = await svc.run_process()

        assert updated.title == "Gourmet Club Sandwich"
        assert updated.servings == 2
        assert updated.note == "Extra mustard"
        assert updated.slot == "lunch"  # preserved

    async def test_toggle_planned_meal_completion(
        self, db_session: AsyncSession, integration_factory
    ):
        meal = await integration_factory.create_planned_meal(slot="dinner")
        assert meal.is_completed is False
        assert meal.completed_by_id is None

        # Toggle to completed
        toggle_svc = PlannedMealToggleService(
            meal=meal,
            user_id=integration_factory.user.id,
            db_session=db_session,
        )
        completed_meal = await toggle_svc.run_process()

        assert completed_meal.is_completed is True
        assert completed_meal.completed_by_id == integration_factory.user.id

        # Toggle back to uncompleted
        toggle_back_svc = PlannedMealToggleService(
            meal=completed_meal,
            user_id=integration_factory.user.id,
            db_session=db_session,
        )
        uncompleted_meal = await toggle_back_svc.run_process()

        assert uncompleted_meal.is_completed is False
        assert uncompleted_meal.completed_by_id is None


class TestGroceryServices:
    """Integration tests for Grocery service operations."""

    async def test_create_single_grocery_item(
        self, db_session: AsyncSession, integration_factory
    ):
        data = GroceryItemCreateSchema(
            name="Organic Milk",
            amount=2.0,
            unit="liters",
            category="dairy",
            added_from_recipe="Oatmeal",
        )
        svc = GroceryItemCreatorService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        item = await svc.run_process()

        assert item.id is not None
        assert item.name == "Organic Milk"
        assert item.amount == 2.0
        assert item.unit == "liters"
        assert item.category == "dairy"
        assert item.is_bought is False
        assert item.added_from_recipe == "Oatmeal"
        assert item.created_by_id == integration_factory.user.id

        # Query back from DB
        result = await db_session.execute(select(GroceryItem).where(GroceryItem.id == item.id))
        db_item = result.scalar_one()
        assert db_item.name == "Organic Milk"

    async def test_batch_add_grocery_items(
        self, db_session: AsyncSession, integration_factory
    ):
        data = GroceryBatchAddSchema(
            items=[
                GroceryItemCreateSchema(name="Tomatoes", amount=5.0, unit="pcs", category="produce"),
                GroceryItemCreateSchema(name="Mozzarella", amount=200.0, unit="g", category="dairy"),
                GroceryItemCreateSchema(name="Basil", amount=1.0, unit="bunch", category="produce"),
            ]
        )
        svc = GroceryBatchAddService(
            family_id=integration_factory.family.id,
            user_id=integration_factory.user.id,
            data=data,
            db_session=db_session,
        )
        items = await svc.run_process()

        assert len(items) == 3
        names = [i.name for i in items]
        assert "Tomatoes" in names
        assert "Mozzarella" in names
        assert "Basil" in names
        for item in items:
            assert item.is_bought is False
            assert item.family_id == integration_factory.family.id

    async def test_grocery_repository_clear_completed(
        self, db_session: AsyncSession, integration_factory
    ):
        repo = GroceryItemRepository(db_session)
        item1 = await integration_factory.create_grocery_item(name="Cheddar Cheese")
        item2 = await integration_factory.create_grocery_item(name="Butter")

        # Mark item1 as bought
        item1.is_bought = True
        await repo.update(item1)

        # Clear completed should remove item1 and keep item2
        cleared_count = await repo.clear_completed(integration_factory.family.id)
        assert cleared_count == 1

        remaining = await repo.get_family_items(integration_factory.family.id)
        names = [i.name for i in remaining]
        assert "Butter" in names
        assert "Cheddar Cheese" not in names
