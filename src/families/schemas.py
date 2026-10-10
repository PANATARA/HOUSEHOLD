from datetime import date as dt_date, datetime as dt_datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from meals.schemas import GroceryItemResponseSchema, PlannedMealResponseSchema
from users.schemas import UserResponseSchema


class FamilyCreateSchema(BaseModel):
    """Schema for creating a new family"""

    name: str = Field(..., min_length=2, max_length=60)
    icon: str = Field(default="material-symbols:home-rounded", max_length=100)
    icon_color: str = Field(default="#ffffff", max_length=50)
    icon_bg: str = Field(
        default="linear-gradient(135deg, #F97316 0%, #FB7185 100%)", max_length=200
    )


class FamilyResponseSchema(BaseModel):
    id: UUID
    name: str
    icon: str
    icon_color: str
    icon_bg: str
    experience: int

    model_config = ConfigDict(from_attributes=True)


class FamilyStatsResponseSchema(FamilyResponseSchema):
    members_count: int
    total_completed: int
    week_completed: int
    streak: int


class FamilyUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    icon: str | None = Field(default=None, max_length=100)
    icon_color: str | None = Field(default=None, max_length=50)
    icon_bg: str | None = Field(default=None, max_length=200)

    @field_validator("name", "icon", "icon_color", "icon_bg", mode="before")
    @classmethod
    def field_not_none(cls, value, info):
        if value is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return value


class FamilyMembersSchema(BaseModel):
    members: list[UserResponseSchema]


class FamilyMemberStatsSchema(BaseModel):
    member: UserResponseSchema | None
    chore_completion_count: int | None


class FamilyLeadersResponseSchema(BaseModel):
    leaders: list[FamilyMemberStatsSchema]


class FamilyJoinSchema(BaseModel):
    invite_code: str


class InviteTokenSchema(BaseModel):
    invite_token: str
    ttl: int


class EventCreateSchema(BaseModel):
    name: str
    description: str | None = None
    date: dt_datetime
    icon: str
    icon_color: str
    icon_bg: str


class EventUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    date: dt_datetime
    icon: str | None = None
    icon_color: str | None = None
    icon_bg: str | None = None


class EventResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    date: dt_datetime
    icon: str
    icon_color: str
    icon_bg: str
    family_id: UUID


class TodayChoresSummarySchema(BaseModel):
    total: int = Field(0, description="Total planned and quick chores for today")
    active: int = Field(0, description="Active (uncompleted) chores for today")
    completed: int = Field(0, description="Completed chores for today")


class TodayMealsSummarySchema(BaseModel):
    breakfast: list[PlannedMealResponseSchema] = Field(
        default_factory=list, description="Breakfast meals planned for today"
    )
    lunch: list[PlannedMealResponseSchema] = Field(
        default_factory=list, description="Lunch meals planned for today"
    )
    dinner: list[PlannedMealResponseSchema] = Field(
        default_factory=list, description="Dinner meals planned for today"
    )
    snack: list[PlannedMealResponseSchema] = Field(
        default_factory=list, description="Snack meals planned for today"
    )
    total_count: int = Field(0, description="Total meals planned for today")


class TodaySummaryResponseSchema(BaseModel):
    date: dt_date = Field(description="Target date for the summary")
    chores: TodayChoresSummarySchema = Field(
        description="Chores count breakdown for today"
    )
    chores_count: int = Field(
        0, description="Total chores count scheduled for today"
    )
    groceries: list[GroceryItemResponseSchema] = Field(
        default_factory=list, description="Active grocery list items"
    )
    groceries_count: int = Field(
        0, description="Number of items in the grocery list"
    )
    event: EventResponseSchema | None = Field(
        default=None, description="Primary/first family event for today if any"
    )
    events: list[EventResponseSchema] = Field(
        default_factory=list, description="All family events for today"
    )
    meals: TodayMealsSummarySchema = Field(
        description="Meal plan for today broken down by slots"
    )
