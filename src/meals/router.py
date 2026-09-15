import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.permissions import FamilyMemberPermission
from database_connection import get_db
from meals.repository import (
    GroceryItemRepository,
    PlannedMealRepository,
    RecipeRepository,
)
from meals.schemas import (
    GroceryBatchAddSchema,
    GroceryItemCreateSchema,
    GroceryItemResponseSchema,
    GroceryItemUpdateSchema,
    GroceryListResponseSchema,
    PlannedMealCreateSchema,
    PlannedMealResponseSchema,
    PlannedMealsListResponseSchema,
    PlannedMealUpdateSchema,
    RecipeCreateSchema,
    RecipeResponseSchema,
    RecipesListResponseSchema,
    RecipeUpdateSchema,
)
from meals.services import (
    GroceryBatchAddService,
    GroceryItemCreatorService,
    PlannedMealCreatorService,
    PlannedMealToggleService,
    PlannedMealUpdateService,
    RecipeCreatorService,
    RecipeUpdateService,
)
from users.models import User

router = APIRouter(tags=["Meals & Recipe Hub"])


# ─────────────────────────────────────────────────────────────────
# 1. RECIPES (КНИГА РЕЦЕПТОВ)
# ─────────────────────────────────────────────────────────────────


@router.get(
    "/recipes",
    response_model=RecipesListResponseSchema,
    summary="Get family recipes with category and search filtering",
)
async def get_recipes(
    category: str | None = Query(None, description="Category filter (quick, kids, desserts, dinner, favorites, etc.)"),
    search: str | None = Query(None, description="Search query by dish name or description"),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    repo = RecipeRepository(async_session)
    recipes = await repo.get_family_recipes(
        family_id=current_user.family_id,  # type: ignore
        category=category,
        search=search,
    )
    return RecipesListResponseSchema(recipes=recipes)


@router.post(
    "/recipes",
    response_model=RecipeResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a custom dish/recipe to the family recipe book",
)
async def create_custom_recipe(
    body: RecipeCreateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        service = RecipeCreatorService(
            family_id=current_user.family_id,  # type: ignore
            user_id=current_user.id,
            data=body,
            db_session=async_session,
        )
        recipe = await service.run_process()
        return RecipeResponseSchema.model_validate(recipe)


@router.get(
    "/recipes/{recipe_id}",
    response_model=RecipeResponseSchema,
    summary="Get single recipe details",
)
async def get_recipe_by_id(
    recipe_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    repo = RecipeRepository(async_session)
    recipe = await repo.get_by_id(recipe_id)
    if recipe.family_id is not None and recipe.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this recipe",
        )
    return RecipeResponseSchema.model_validate(recipe)


@router.patch(
    "/recipes/{recipe_id}",
    response_model=RecipeResponseSchema,
    summary="Update recipe",
)
async def update_recipe(
    recipe_id: UUID,
    body: RecipeUpdateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = RecipeRepository(async_session)
        recipe = await repo.get_by_id(recipe_id)
        if recipe.family_id is not None and recipe.family_id != current_user.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to edit this recipe",
            )
        service = RecipeUpdateService(
            recipe=recipe,
            data=body,
            db_session=async_session,
        )
        updated = await service.run_process()
        return RecipeResponseSchema.model_validate(updated)


@router.post(
    "/recipes/{recipe_id}/favorite",
    response_model=RecipeResponseSchema,
    summary="Toggle recipe favorite status",
)
async def toggle_recipe_favorite(
    recipe_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = RecipeRepository(async_session)
        recipe = await repo.get_by_id(recipe_id)
        updated = await repo.toggle_favorite(recipe)
        return RecipeResponseSchema.model_validate(updated)


@router.delete(
    "/recipes/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete custom recipe",
)
async def delete_recipe(
    recipe_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = RecipeRepository(async_session)
        recipe = await repo.get_by_id(recipe_id)
        if recipe.family_id != current_user.family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only custom family recipes can be deleted",
            )
        await repo.soft_delete(recipe_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────
# 2. WEEKLY MEAL PLANNER (РАСПИСАНИЕ ПИТАНИЯ)
# ─────────────────────────────────────────────────────────────────


@router.get(
    "/planner",
    response_model=PlannedMealsListResponseSchema,
    summary="Get planned meals for a date range (defaults to current week)",
)
async def get_planned_meals(
    start_date: datetime.date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    today = datetime.date.today()
    if start_date is None:
        start_date = today - datetime.timedelta(days=today.weekday())  # Monday
    if end_date is None:
        end_date = start_date + datetime.timedelta(days=6)  # Sunday

    repo = PlannedMealRepository(async_session)
    meals = await repo.get_family_meals(
        family_id=current_user.family_id,  # type: ignore
        start_date=start_date,
        end_date=end_date,
    )
    return PlannedMealsListResponseSchema(
        meals=[PlannedMealResponseSchema.model_validate(m) for m in meals]
    )


@router.post(
    "/planner",
    response_model=PlannedMealResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a meal for a date and slot",
)
async def create_planned_meal(
    body: PlannedMealCreateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        service = PlannedMealCreatorService(
            family_id=current_user.family_id,  # type: ignore
            user_id=current_user.id,
            data=body,
            db_session=async_session,
        )
        meal = await service.run_process()
        return PlannedMealResponseSchema.model_validate(meal)


@router.patch(
    "/planner/{meal_id}",
    response_model=PlannedMealResponseSchema,
    summary="Update planned meal details",
)
async def update_planned_meal(
    meal_id: UUID,
    body: PlannedMealUpdateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = PlannedMealRepository(async_session)
        meal = await repo.get_by_id_with_relations(meal_id)
        if meal.family_id != current_user.family_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        service = PlannedMealUpdateService(
            meal=meal,
            data=body,
            db_session=async_session,
        )
        updated = await service.run_process()
        return PlannedMealResponseSchema.model_validate(updated)


@router.post(
    "/planner/{meal_id}/toggle",
    response_model=PlannedMealResponseSchema,
    summary="Toggle meal cooked/completed status",
)
async def toggle_meal_completed(
    meal_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = PlannedMealRepository(async_session)
        meal = await repo.get_by_id_with_relations(meal_id)
        if meal.family_id != current_user.family_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        service = PlannedMealToggleService(
            meal=meal,
            user_id=current_user.id,
            db_session=async_session,
        )
        updated = await service.run_process()
        return PlannedMealResponseSchema.model_validate(updated)


@router.delete(
    "/planner/{meal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete planned meal",
)
async def delete_planned_meal(
    meal_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = PlannedMealRepository(async_session)
        meal = await repo.get_by_id(meal_id)
        if meal.family_id != current_user.family_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        await repo.hard_delete(meal_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────
# 3. GROCERY LIST (СПИСОК ПОКУПОК)
# ─────────────────────────────────────────────────────────────────


@router.get(
    "/groceries",
    response_model=GroceryListResponseSchema,
    summary="Get family grocery shopping list",
)
async def get_groceries(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    repo = GroceryItemRepository(async_session)
    items = await repo.get_family_items(current_user.family_id)  # type: ignore
    return GroceryListResponseSchema(
        items=[GroceryItemResponseSchema.model_validate(i) for i in items]
    )


@router.post(
    "/groceries",
    response_model=GroceryItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to the grocery shopping list",
)
async def add_grocery_item(
    body: GroceryItemCreateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        service = GroceryItemCreatorService(
            family_id=current_user.family_id,  # type: ignore
            user_id=current_user.id,
            data=body,
            db_session=async_session,
        )
        item = await service.run_process()
        return GroceryItemResponseSchema.model_validate(item)


@router.post(
    "/groceries/batch",
    response_model=GroceryListResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a batch of ingredients to the grocery list",
)
async def add_grocery_batch(
    body: GroceryBatchAddSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        service = GroceryBatchAddService(
            family_id=current_user.family_id,  # type: ignore
            user_id=current_user.id,
            data=body,
            db_session=async_session,
        )
        items = await service.run_process()
        return GroceryListResponseSchema(
            items=[GroceryItemResponseSchema.model_validate(i) for i in items]
        )


@router.patch(
    "/groceries/{item_id}",
    response_model=GroceryItemResponseSchema,
    summary="Update or toggle bought status of grocery item",
)
async def update_grocery_item(
    item_id: UUID,
    body: GroceryItemUpdateSchema,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = GroceryItemRepository(async_session)
        item = await repo.get_by_id(item_id)
        if item.family_id != current_user.family_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(item, field, value)

        await repo.update(item)
        return GroceryItemResponseSchema.model_validate(item)


@router.delete(
    "/groceries/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete single grocery item",
)
async def delete_grocery_item(
    item_id: UUID,
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = GroceryItemRepository(async_session)
        item = await repo.get_by_id(item_id)
        if item.family_id != current_user.family_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        await repo.hard_delete(item_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/groceries",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all completed / bought items from grocery list",
)
async def clear_bought_groceries(
    current_user: User = Depends(FamilyMemberPermission()),
    async_session: AsyncSession = Depends(get_db),
):
    async with async_session.begin():
        repo = GroceryItemRepository(async_session)
        await repo.clear_completed(current_user.family_id)  # type: ignore
        return Response(status_code=status.HTTP_204_NO_CONTENT)
