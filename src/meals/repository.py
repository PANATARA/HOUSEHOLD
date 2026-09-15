import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.meals import (
    GroceryItemNotFoundError,
    PlannedMealNotFoundError,
    RecipeNotFoundError,
)
from meals.models import GroceryItem, PlannedMeal, Recipe


class RecipeRepository(BaseDals[Recipe], DeleteDALMixin):
    model = Recipe
    not_found_exception = RecipeNotFoundError

    async def get_family_recipes(
        self,
        family_id: UUID,
        category: str | None = None,
        search: str | None = None,
    ) -> list[Recipe]:
        query = select(Recipe).where(
            Recipe.family_id == family_id,
            Recipe.is_active,
        )

        if category and category != "all" and category != "favorites":
            query = query.where(Recipe.category == category)
        elif category == "favorites":
            query = query.where(Recipe.is_favorite.is_(True))

        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    Recipe.title.ilike(pattern),
                    Recipe.description.ilike(pattern),
                )
            )

        query = query.order_by(Recipe.is_favorite.desc(), Recipe.created_at.desc())
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def toggle_favorite(self, recipe: Recipe) -> Recipe:
        recipe.is_favorite = not recipe.is_favorite
        await self.update(recipe)
        return recipe


class PlannedMealRepository(BaseDals[PlannedMeal], DeleteDALMixin):
    model = PlannedMeal
    not_found_exception = PlannedMealNotFoundError

    async def get_family_meals(
        self,
        family_id: UUID,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[PlannedMeal]:
        query = (
            select(PlannedMeal)
            .where(
                PlannedMeal.family_id == family_id,
                PlannedMeal.date >= start_date,
                PlannedMeal.date <= end_date,
                PlannedMeal.is_active,
            )
            .options(
                selectinload(PlannedMeal.cook),
                selectinload(PlannedMeal.completed_by),
                selectinload(PlannedMeal.recipe),
            )
            .order_by(PlannedMeal.date.asc(), PlannedMeal.created_at.asc())
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_id_with_relations(self, meal_id: UUID) -> PlannedMeal:
        query = (
            select(PlannedMeal)
            .where(PlannedMeal.id == meal_id)
            .options(
                selectinload(PlannedMeal.cook),
                selectinload(PlannedMeal.completed_by),
                selectinload(PlannedMeal.recipe),
            )
        )
        result = await self.db_session.execute(query)
        meal = result.scalar_one_or_none()
        if not meal:
            raise PlannedMealNotFoundError
        return meal


class GroceryItemRepository(BaseDals[GroceryItem], DeleteDALMixin):
    model = GroceryItem
    not_found_exception = GroceryItemNotFoundError

    async def get_family_items(self, family_id: UUID) -> list[GroceryItem]:
        query = (
            select(GroceryItem)
            .where(
                GroceryItem.family_id == family_id,
                GroceryItem.is_active,
            )
            .order_by(GroceryItem.is_bought.asc(), GroceryItem.created_at.desc())
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def create_batch(self, items: list[GroceryItem]) -> list[GroceryItem]:
        self.db_session.add_all(items)
        await self.db_session.flush()
        for item in items:
            await self.db_session.refresh(item)
        return items

    async def clear_completed(self, family_id: UUID) -> int:
        query = delete(GroceryItem).where(
            GroceryItem.family_id == family_id,
            GroceryItem.is_bought.is_(True),
        )
        res = await self.db_session.execute(query)
        return res.rowcount or 0
