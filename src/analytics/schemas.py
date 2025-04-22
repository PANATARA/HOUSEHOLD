from datetime import date
from uuid import UUID
from pydantic import BaseModel


class ChoreAnalyticSchema(BaseModel):
    family_id: str
    chore_id: str
    user_id: str
    completion_date: date


class DateRange(BaseModel):
    date_start: date
    date_end: date


class TopMemberByChoreCompletion(BaseModel):
    id: UUID
    total_completion_chore: int