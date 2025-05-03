from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from chores.schemas import ChoreResponseSchema
from core.enums import StatusConfirmENUM
from users.schemas import UserResponseSchema


class ChoreCompletionCreateSchema(BaseModel):
    message: str


class ChoreCompletionResponseSchema(BaseModel):
    id: UUID
    chore: ChoreResponseSchema
    completed_by: UserResponseSchema
    completed_at: datetime
    status: str
    message: str


class ChoreCompletionDetailSchema(BaseModel):
    class ConfirmedBySchema(BaseModel):
        user: UserResponseSchema
        status: StatusConfirmENUM

    chore_completion: ChoreCompletionResponseSchema
    confirmed_by: list[ConfirmedBySchema | None]
