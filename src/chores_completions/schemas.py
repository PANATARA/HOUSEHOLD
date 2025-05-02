from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from chores.schemas import ChoreSchema
from core.enums import StatusConfirmENUM
from users.schemas import UserResponseSchema


class ChoreCompletionCreateSchema(BaseModel):
    message: str


class ChoreCompletionSchema(BaseModel):
    id: UUID
    chore: ChoreSchema
    completed_by: UserResponseSchema
    completed_at: datetime
    status: str
    message: str


class ChoreCompletionSummaryLiteSchema(BaseModel):
    """Schema for user's wallet transactions"""

    id: UUID
    chore: ChoreSchema
    completed_at: datetime


class ChoreConfirmationSummarySchema(BaseModel):
    user: UserResponseSchema
    status: StatusConfirmENUM


class ChoreCompletionDetailSchema(BaseModel):
    chore_completion: ChoreCompletionSchema
    confirmed_by: list[ChoreConfirmationSummarySchema | None]
