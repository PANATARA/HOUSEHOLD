from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.chores.chores import NewChoreDetail, NewChoreSummary
from schemas.chores.chores_completions import (
    NewChoreCompletion,
    NewChoreCompletionSummary,
)
from schemas.chores.chores_confirmations import NewChoreConfirmationSummary
from schemas.users import UserSummarySchema


class NewChoreCompletionDetail(BaseModel):
    id: UUID
    chore: NewChoreSummary
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str
    confirmed_by: list[NewChoreConfirmationSummary | None]


class NewChoreConfirmationDetail(BaseModel):
    """Only for a specific user"""

    id: UUID
    chore_completion: NewChoreCompletionSummary
    status: StatusConfirmENUM


class NewChoreDetailMax(BaseModel):
    chore: NewChoreDetail
    chores_completion: list[NewChoreCompletion | None]
