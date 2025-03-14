from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from schemas.chores.chores import NewChoreSummary
from schemas.users import UserSummarySchema


class NewChoreCompletionCreate(BaseModel):
    message: str


class NewChoreCompletionSummaryLite(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_at: datetime


class NewChoreCompletionSummary(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str

class NewChoreCompletion(BaseModel):
    id: UUID
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str
