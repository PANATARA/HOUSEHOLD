import datetime
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from chores.schemas import ChoreResponseSchema
from core.enums import FrequencyTypeENUM
from users.schemas import UserResponseSchema


class PlannedChoreCreateSchema(BaseModel):
    assigned_to_id: UUID | None = None
    due_date: date
    message: str = Field(default="", max_length=1000)


class PlannedChoreRescheduleSchema(BaseModel):
    reschedule_due_date: date


class PlannedChoreUpdateMessageSchema(BaseModel):
    message: str = Field(..., max_length=2000)


# Backward compatibility aliases
PlannedChoreUpdateSchema = PlannedChoreUpdateMessageSchema
UpdatePlannedChoreMessageSchema = PlannedChoreUpdateMessageSchema


class PlannedChoreResponseSchema(BaseModel):
    id: UUID
    schedule_id: UUID | None = None
    chore: ChoreResponseSchema
    completed_by: UserResponseSchema | None = None
    assigned_to: UserResponseSchema | None = None
    due_date: date
    message: str

    model_config = {"from_attributes": True}


class ChoreScheduleCreateSchema(BaseModel):
    assigned_to_id: UUID
    frequency_type: FrequencyTypeENUM
    interval: int = Field(default=1, ge=1)
    days_of_week: int | None = None
    day_of_month: int | None = None
    starts_at: date
    ends_at: date | None = None

    @model_validator(mode="after")
    def validate_frequency_specific_fields(self) -> "ChoreScheduleCreateSchema":
        if self.frequency_type == FrequencyTypeENUM.weekly:
            if self.days_of_week is None:
                raise ValueError("days_of_week is required for weekly frequency")
            if not (1 <= self.days_of_week <= 127):
                raise ValueError("days_of_week bitmask must be between 1 and 127")
        elif self.frequency_type == FrequencyTypeENUM.monthly:
            if self.day_of_month is None:
                raise ValueError("day_of_month is required for monthly frequency")
            if not (1 <= self.day_of_month <= 31):
                raise ValueError("day_of_month must be between 1 and 31")

        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at cannot be before starts_at")

        return self


# Backward compatibility alias
CreateChoreScheduleSchema = ChoreScheduleCreateSchema


class ChoreScheduleUpdateSchema(BaseModel):
    assigned_to_id: UUID | None = None
    frequency_type: FrequencyTypeENUM | None = None
    interval: int | None = Field(default=None, ge=1)
    days_of_week: int | None = None
    day_of_month: int | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_frequency_specific_fields(self) -> "ChoreScheduleUpdateSchema":
        if self.frequency_type == FrequencyTypeENUM.weekly:
            if self.days_of_week is None:
                raise ValueError("days_of_week is required for weekly frequency")
        elif self.frequency_type == FrequencyTypeENUM.monthly:
            if self.day_of_month is None:
                raise ValueError("day_of_month is required for monthly frequency")

        if self.days_of_week is not None and not (1 <= self.days_of_week <= 127):
            raise ValueError("days_of_week bitmask must be between 1 and 127")

        if self.day_of_month is not None and not (1 <= self.day_of_month <= 31):
            raise ValueError("day_of_month must be between 1 and 31")

        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at < self.starts_at
        ):
            raise ValueError("ends_at cannot be before starts_at")

        return self


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
    starts_at: date
    ends_at: date | None
    last_generated_until: date | None = None
    is_active: bool
    created_by: UUID | None = None


class QuickPlannedChoreCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str = Field(default="material-symbols:bolt-rounded", max_length=100)
    icon_color: str = Field(default="#ffffff", max_length=50)
    icon_bg: str = Field(default="linear-gradient(135deg, #F59E0B 0%, #F97316 100%)", max_length=200)
    valuation: int = Field(default=10, ge=0, le=100000)
    assigned_to_id: UUID | None = None
    due_date: datetime.date
    message: str = Field(default="", max_length=1000)


class QuickPlannedChoreUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=100)
    icon_color: str | None = Field(default=None, max_length=50)
    icon_bg: str | None = Field(default=None, max_length=200)
    valuation: int | None = Field(default=None, ge=0, le=100000)
    assigned_to_id: UUID | None = None
    due_date: datetime.date | None = None
    message: str | None = Field(default=None, max_length=1000)


class QuickPlannedChoreUserSchema(BaseModel):
    id: UUID
    name: str
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
