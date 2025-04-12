from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from chores.schemas import ChoreSchema
from users.schemas import UserSummarySchema


class ChoreCompletionCreateSchema(BaseModel):
    message: str


class ChoreCompletionSchema(BaseModel):
    id: UUID
    chore: ChoreSchema
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str


class ChoreCompletionSummaryLiteSchema(BaseModel):
    """Schema for user's wallet transactions"""

    id: UUID
    chore: ChoreSchema
    completed_at: datetime


class ChoreCompletionLiteSchema(BaseModel):
    id: UUID
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str


from chores_confirmations.schemas import NewChoreConfirmationSummary  # noqa: E402


class NewChoreCompletionDetail(BaseModel):
    id: UUID
    chore: ChoreSchema
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str
    confirmed_by: list[NewChoreConfirmationSummary | None]
