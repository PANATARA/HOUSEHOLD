import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── INGREDIENTS & STEPS ──────────────────────────────────────────


class IngredientSchema(BaseModel):
    id: str | None = None
    name: str
    amount: float | int | None = None
    unit: str = ""
    checked: bool = False

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        if v == "" or v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class RecipeStepSchema(BaseModel):
    number: int
    text: str


# ─── RECIPES ───────────────────────────────────────────────────────


class RecipeCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    prep_time_minutes: int = Field(default=10, ge=0)
    cook_time_minutes: int = Field(default=20, ge=0)
    base_servings: int = Field(default=4, ge=1)
    category: str = Field(default="quick", max_length=50)
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    accent_gradient: str = Field(
        default="linear-gradient(135deg, #F97316 0%, #EA580C 100%)",
        max_length=200,
    )
    emoji: str = Field(default="🍲", max_length=16)
    ingredients: list[IngredientSchema] = Field(default_factory=list)
    steps: list[RecipeStepSchema] = Field(default_factory=list)


class RecipeUpdateSchema(BaseModel):
    title: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    prep_time_minutes: int | None = Field(default=None, ge=0)
    cook_time_minutes: int | None = Field(default=None, ge=0)
    base_servings: int | None = Field(default=None, ge=1)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = None
    is_favorite: bool | None = None
    accent_gradient: str | None = Field(default=None, max_length=200)
    emoji: str | None = Field(default=None, max_length=16)
    ingredients: list[IngredientSchema] | None = None
    steps: list[RecipeStepSchema] | None = None


class RecipeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID | None = None
    created_by_id: UUID | None = None
    title: str
    description: str | None = None
    prep_time_minutes: int
    cook_time_minutes: int
    base_servings: int
    category: str
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool
    is_custom: bool
    accent_gradient: str
    emoji: str
    ingredients: list[IngredientSchema] = Field(default_factory=list)
    steps: list[RecipeStepSchema] = Field(default_factory=list)
    created_at: datetime.datetime


class RecipesListResponseSchema(BaseModel):
    recipes: list[RecipeResponseSchema]


# ─── PLANNED MEALS (PLANNER) ──────────────────────────────────────


class CookBriefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None
    icon: str | None = "material-symbols:person-rounded"
    icon_bg: str | None = "#FFE8E0"
    icon_color: str | None = "#E06A47"


class PlannedMealCreateSchema(BaseModel):
    date: datetime.date
    slot: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    title: str = Field(..., min_length=1, max_length=128)
    prep_time_minutes: int = Field(default=15, ge=0)
    recipe_id: UUID | None = None
    assigned_cook_id: UUID | None = None
    servings: int = Field(default=4, ge=1)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("recipe_id", "assigned_cook_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class PlannedMealUpdateSchema(BaseModel):
    date: datetime.date | None = None
    slot: str | None = Field(default=None, pattern="^(breakfast|lunch|dinner|snack)$")
    title: str | None = Field(default=None, max_length=128)
    prep_time_minutes: int | None = Field(default=None, ge=0)
    recipe_id: UUID | None = None
    assigned_cook_id: UUID | None = None
    servings: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=500)
    is_completed: bool | None = None

    @field_validator("recipe_id", "assigned_cook_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class PlannedMealResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    date: datetime.date
    slot: str
    title: str
    prep_time_minutes: int
    recipe_id: UUID | None = None
    assigned_cook_id: UUID | None = None
    cook: CookBriefSchema | None = None
    servings: int
    note: str | None = None
    is_completed: bool
    completed_by_id: UUID | None = None
    completed_by: CookBriefSchema | None = None
    created_at: datetime.datetime


class PlannedMealsListResponseSchema(BaseModel):
    meals: list[PlannedMealResponseSchema]


# ─── GROCERY ITEMS ────────────────────────────────────────────────


class GroceryItemCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    amount: float | None = None
    unit: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=50)
    added_from_recipe: str | None = Field(default=None, max_length=128)


class GroceryBatchAddSchema(BaseModel):
    items: list[GroceryItemCreateSchema]


class GroceryItemUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    amount: float | None = None
    unit: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=50)
    is_bought: bool | None = None


class GroceryItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    name: str
    amount: float | None = None
    unit: str | None = None
    category: str | None = None
    is_bought: bool
    added_from_recipe: str | None = None
    created_at: datetime.datetime


class GroceryListResponseSchema(BaseModel):
    items: list[GroceryItemResponseSchema]
