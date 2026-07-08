from datetime import date
import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from chores.schemas import ChoreResponseSchema
from core.enums import FrequencyTypeENUM
from users.schemas import UserResponseSchema


class PlannedChoreCreateSchema(BaseModel):
    assigned_to_id: UUID | None
    due_date: date
    message: str


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
