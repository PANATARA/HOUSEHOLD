from uuid import UUID

from pydantic import BaseModel, field_validator

from core.constants import StatusConfirmENUM
from schemas.users import UserSummarySchema


class NewChoreConfirmationSummary(BaseModel):
    id: UUID
    user: UserSummarySchema
    status: StatusConfirmENUM


class NewChoreConfirmationSetStatus(BaseModel):
    status: StatusConfirmENUM

    @field_validator("status")
    def validate_status(cls, v):
        if v == StatusConfirmENUM.awaits:
            raise ValueError("Setting status to 'awaits' is not allowed")
        return v
