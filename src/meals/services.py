import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.services import BaseService
from meals.models import GroceryItem, PlannedMeal, Recipe
from meals.repository import (
    GroceryItemRepository,
    PlannedMealRepository,
    RecipeRepository,
)
from meals.schemas import (
    GroceryBatchAddSchema,
    GroceryItemCreateSchema,
    PlannedMealCreateSchema,
    PlannedMealUpdateSchema,
    RecipeCreateSchema,
    RecipeUpdateSchema,
)


@dataclass
class RecipeCreatorService(BaseService[Recipe]):
    """Creates a custom family recipe in the recipe box."""

    family_id: uuid.UUID
    user_id: uuid.UUID
    data: RecipeCreateSchema
    db_session: AsyncSession

    async def process(self) -> Recipe:
        repo = RecipeRepository(self.db_session)
        recipe = Recipe(
            family_id=self.family_id,
            created_by_id=self.user_id,
            title=self.data.title,
            description=self.data.description,
            prep_time_minutes=self.data.prep_time_minutes,
            cook_time_minutes=self.data.cook_time_minutes,
            base_servings=self.data.base_servings,
            category=self.data.category,
            tags=self.data.tags,
            is_favorite=self.data.is_favorite,
            is_custom=True,
            accent_gradient=self.data.accent_gradient,
            emoji=self.data.emoji,
            ingredients=[ing.model_dump() for ing in self.data.ingredients],
            steps=[step.model_dump() for step in self.data.steps],
            is_active=True,
        )
        return await repo.create(recipe)


@dataclass
class RecipeUpdateService(BaseService[Recipe]):
    recipe: Recipe
    data: RecipeUpdateSchema
    db_session: AsyncSession

    async def process(self) -> Recipe:
        repo = RecipeRepository(self.db_session)
        update_data = self.data.model_dump(exclude_unset=True)

        if "ingredients" in update_data and update_data["ingredients"] is not None:
            update_data["ingredients"] = [
                ing.model_dump() if hasattr(ing, "model_dump") else ing
                for ing in self.data.ingredients or []
            ]
        if "steps" in update_data and update_data["steps"] is not None:
            update_data["steps"] = [
                step.model_dump() if hasattr(step, "model_dump") else step
                for step in self.data.steps or []
            ]

        for field, value in update_data.items():
            setattr(self.recipe, field, value)

        await repo.update(self.recipe)
        return self.recipe


@dataclass
class PlannedMealCreatorService(BaseService[PlannedMeal]):
    family_id: uuid.UUID
    user_id: uuid.UUID
    data: PlannedMealCreateSchema
    db_session: AsyncSession

    async def process(self) -> PlannedMeal:
        repo = PlannedMealRepository(self.db_session)
        meal = PlannedMeal(
            family_id=self.family_id,
            date=self.data.date,
            slot=self.data.slot,
            title=self.data.title,
            prep_time_minutes=self.data.prep_time_minutes,
            recipe_id=self.data.recipe_id,
            assigned_cook_id=self.data.assigned_cook_id,
            servings=self.data.servings,
            note=self.data.note,
            is_completed=False,
            created_by_id=self.user_id,
            is_active=True,
        )
        await repo.create(meal)
        return await repo.get_by_id_with_relations(meal.id)


@dataclass
class PlannedMealUpdateService(BaseService[PlannedMeal]):
    meal: PlannedMeal
    data: PlannedMealUpdateSchema
    db_session: AsyncSession

    async def process(self) -> PlannedMeal:
        repo = PlannedMealRepository(self.db_session)
        for field, value in self.data.model_dump(exclude_unset=True).items():
            setattr(self.meal, field, value)
        await repo.update(self.meal)
        return await repo.get_by_id_with_relations(self.meal.id)


@dataclass
class PlannedMealToggleService(BaseService[PlannedMeal]):
    meal: PlannedMeal
    user_id: uuid.UUID
    db_session: AsyncSession

    async def process(self) -> PlannedMeal:
        repo = PlannedMealRepository(self.db_session)
        if self.meal.is_completed:
            self.meal.is_completed = False
            self.meal.completed_by_id = None
        else:
            self.meal.is_completed = True
            self.meal.completed_by_id = self.user_id

        await repo.update(self.meal)
        return await repo.get_by_id_with_relations(self.meal.id)


@dataclass
class GroceryItemCreatorService(BaseService[GroceryItem]):
    family_id: uuid.UUID
    user_id: uuid.UUID
    data: GroceryItemCreateSchema
    db_session: AsyncSession

    async def process(self) -> GroceryItem:
        repo = GroceryItemRepository(self.db_session)
        item = GroceryItem(
            family_id=self.family_id,
            name=self.data.name,
            amount=self.data.amount,
            unit=self.data.unit,
            category=self.data.category,
            is_bought=False,
            added_from_recipe=self.data.added_from_recipe,
            created_by_id=self.user_id,
            is_active=True,
        )
        return await repo.create(item)


@dataclass
class GroceryBatchAddService(BaseService[list[GroceryItem]]):
    family_id: uuid.UUID
    user_id: uuid.UUID
    data: GroceryBatchAddSchema
    db_session: AsyncSession

    async def process(self) -> list[GroceryItem]:
        repo = GroceryItemRepository(self.db_session)
        items: list[GroceryItem] = []
        for item_data in self.data.items:
            items.append(
                GroceryItem(
                    family_id=self.family_id,
                    name=item_data.name,
                    amount=item_data.amount,
                    unit=item_data.unit,
                    category=item_data.category,
                    is_bought=False,
                    added_from_recipe=item_data.added_from_recipe,
                    created_by_id=self.user_id,
                    is_active=True,
                )
            )
        return await repo.create_batch(items)
