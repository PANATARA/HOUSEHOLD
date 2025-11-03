from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DateRangeSchema(BaseModel):
    start: datetime | None = Field(
        None, description="Start date of the interval (inclusive)"
    )
    end: datetime | None = Field(
        None, description="End date of the interval (inclusive)"
    )


class UserChoresCountSchema(BaseModel):
    user_id: UUID
    chores_completions_counts: int


class ActivitySchema(BaseModel):
    activity_date: date
    activity: int


class UserActivitySchema(BaseModel):
    activities: list[ActivitySchema]


class ChoresFamilyCountSchema(BaseModel):
    chore_id: UUID
    chores_completions_counts: int
