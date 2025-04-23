from uuid import UUID

from pydantic import BaseModel, field_validator

from chores_completions.schemas import ChoreCompletionSchema
from core.enums import StatusConfirmENUM
from users.schemas import UserSummarySchema


class ChoreConfirmationSummarySchema(BaseModel):
    id: UUID
    user: UserSummarySchema
    status: StatusConfirmENUM


class ChoreConfirmationSetStatusSchema(BaseModel):
    status: StatusConfirmENUM

    @field_validator("status")
    def validate_status(cls, v):
        if v == StatusConfirmENUM.awaits:
            raise ValueError("Setting status to 'awaits' is not allowed")
        return v


class ChoreConfirmationDetailSchema(BaseModel):
    """Only for a specific user"""

    id: UUID
    chore_completion: ChoreCompletionSchema
    status: StatusConfirmENUM
