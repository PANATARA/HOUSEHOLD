from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.chores import NewChoreSummary
from schemas.users import UserResponse


class NewChoreCompletionSummaryLite(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_at: datetime


class NewChoreCompletionSummary(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_by: UserResponse
    completed_at: datetime
    status: str


class NewChoreCompletionCreate(BaseModel):
    chore_id: UUID
    message: str


class NewChoreConfirmationDetail(BaseModel):
    """Only for a specific user"""
    id: UUID
    chore_completion: NewChoreCompletionSummary
    status: StatusConfirmENUM


class NewChoreConfirmationSummary(BaseModel):
    id: UUID
    user: UserResponse
    status: StatusConfirmENUM


class NewChoreConfirmationSetStatus(BaseModel):
    status: StatusConfirmENUM

class NewChoreCompletionDetail(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_by: UserResponse
    completed_at: datetime
    status: str
    message: str
    confirmed_by: list[NewChoreConfirmationSummary | None]