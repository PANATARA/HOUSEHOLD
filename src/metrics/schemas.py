from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DateRangeSchema(BaseModel):
    start: datetime | None
    end: datetime | None


class ActivityItem(BaseModel):
    activity_date: date
    activity: int


class ChoreItem(BaseModel):
    chore_id: UUID
    chores_completions_counts: int


class FamilyMember(BaseModel):
    user_id: UUID
    chores_completions_counts: int


class ActivitiesResponse(BaseModel):
    activities: list[ActivityItem]
