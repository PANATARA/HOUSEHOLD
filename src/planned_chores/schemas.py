import datetime
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from chores.schemas import ChoreResponseSchema
from core.enums import FrequencyTypeENUM
from users.schemas import UserResponseSchema


class PlannedChoreCreateSchema(BaseModel):
    assigned_to_id: UUID | None
    due_date: date
    message: str


class PlannedChoreRescheduleSchema(BaseModel):
    reschedule_due_date: date


class PlannedChoreResponseSchema(BaseModel):
    id: UUID
    chore: ChoreResponseSchema
    completed_by: UserResponseSchema | None = None
    assigned_to: UserResponseSchema | None = None
    due_date: date
    message: str

    model_config = {"from_attributes": True}


class CreateChoreScheduleSchema(BaseModel):
    assigned_to_id: UUID
    frequency_type: FrequencyTypeENUM
    interval: int = 1
    days_of_week: int | None = None
    day_of_month: int | None = None
    starts_at: datetime.date
    ends_at: datetime.date | None = None


class ChoreScheduleResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chore_id: UUID
    family_id: UUID
    assigned_to_id: UUID
    frequency_type: FrequencyTypeENUM
    interval: int
    days_of_week: int | None
    day_of_month: int | None
    starts_at: datetime.date
    ends_at: datetime.date | None
    is_active: bool


class QuickPlannedChoreCreateSchema(BaseModel):
    name: str
    description: str | None = None
    icon: str = "material-symbols:bolt-rounded"
    icon_color: str = "#ffffff"
    icon_bg: str = "linear-gradient(135deg, #F59E0B 0%, #F97316 100%)"
    valuation: int
    assigned_to_id: UUID | None = None
    due_date: datetime.date
    message: str = Field(default="", max_length=50)


class QuickPlannedChoreUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    icon_color: str | None = None
    icon_bg: str | None = None
    valuation: int | None = None
    assigned_to_id: UUID | None = None
    due_date: datetime.date | None = None
    message: str | None = Field(default=None, max_length=50)


class QuickPlannedChoreUserSchema(BaseModel):
    id: UUID
    name: str
    surname: str
    icon: str
    icon_color: str
    icon_bg: str
    experience: int

    model_config = {"from_attributes": True}


class QuickPlannedChoreResponseSchema(BaseModel):
    id: UUID
    name: str
    description: str | None
    icon: str
    icon_color: str
    icon_bg: str
    valuation: int
    family_id: UUID
    is_active: bool
    completed_by: QuickPlannedChoreUserSchema | None
    assigned_to: QuickPlannedChoreUserSchema | None
    due_date: datetime.date
    message: str
    created_by: UUID | None

    model_config = {"from_attributes": True}
