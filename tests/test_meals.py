import datetime
import uuid
import pytest
from pydantic import ValidationError

from meals.schemas import (
    GroceryBatchAddSchema,
    GroceryItemCreateSchema,
    IngredientSchema,
    PlannedMealCreateSchema,
    RecipeCreateSchema,
    RecipeStepSchema,
)


def test_valid_recipe_create_schema():
    recipe_data = RecipeCreateSchema(
        title="Домашняя пицца Маргарита",
        description="Хрустящее тесто, томатный соус и моцарелла",
        prep_time_minutes=20,
        cook_time_minutes=15,
        base_servings=4,
        category="dinner",
        tags=["Пицца", "Италия", "Выпечка"],
        is_favorite=True,
        emoji="🍕",
        accent_gradient="linear-gradient(135deg, #EF4444 0%, #B91C1C 100%)",
        ingredients=[
            IngredientSchema(name="Мука", amount=300, unit="г"),
            IngredientSchema(name="Моцарелла", amount=200, unit="г"),
            IngredientSchema(name="Томатный соус", amount=100, unit="г"),
        ],
        steps=[
            RecipeStepSchema(number=1, text="Замесить дрожжевое тесто."),
            RecipeStepSchema(number=2, text="Раскатать круг и выложить начинку."),
            RecipeStepSchema(number=3, text="Выпекать 12 минут при 220 градусах."),
        ],
    )
    assert recipe_data.title == "Домашняя пицца Маргарита"
    assert recipe_data.base_servings == 4
    assert len(recipe_data.ingredients) == 3
    assert len(recipe_data.steps) == 3
    assert recipe_data.ingredients[0].name == "Мука"


def test_recipe_create_schema_invalid_empty_title():
    with pytest.raises(ValidationError):
        RecipeCreateSchema(title="")


def test_valid_planned_meal_create_schema():
    today = datetime.date.today()
    meal_data = PlannedMealCreateSchema(
        date=today,
        slot="dinner",
        title="Сливочная паста с курицей",
        prep_time_minutes=20,
        recipe_id=uuid.uuid4(),
        assigned_cook_id=uuid.uuid4(),
        servings=4,
        note="Купить свежий базилик",
    )
    assert meal_data.date == today
    assert meal_data.slot == "dinner"
    assert meal_data.servings == 4


def test_planned_meal_invalid_slot():
    today = datetime.date.today()
    with pytest.raises(ValidationError):
        PlannedMealCreateSchema(
            date=today,
            slot="midnight_snack",  # invalid slot, must be breakfast/lunch/dinner/snack
            title="Перекус",
        )


def test_valid_grocery_batch_add_schema():
    batch = GroceryBatchAddSchema(
        items=[
            GroceryItemCreateSchema(
                name="Сливки 20%",
                amount=250,
                unit="мл",
                added_from_recipe="Сливочная паста",
            ),
            GroceryItemCreateSchema(
                name="Пармезан",
                amount=60,
                unit="г",
                added_from_recipe="Сливочная паста",
            ),
        ]
    )
    assert len(batch.items) == 2
    assert batch.items[0].name == "Сливки 20%"
    assert batch.items[1].unit == "г"
