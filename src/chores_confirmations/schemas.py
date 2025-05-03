from uuid import UUID

from pydantic import BaseModel, field_validator

from chores_completions.schemas import ChoreCompletionResponseSchema
from core.enums import StatusConfirmENUM


class ChoreConfirmationSetStatusSchema(BaseModel):
    status: StatusConfirmENUM

    @field_validator("status")
    def validate_status(cls, v):
        if v == StatusConfirmENUM.awaits:
            raise ValueError("Setting status to 'awaits' is not allowed")
        return v


class ChoreConfirmationResponseSchema(BaseModel):
    id: UUID
    chore_completion: ChoreCompletionResponseSchema
    status: StatusConfirmENUM
