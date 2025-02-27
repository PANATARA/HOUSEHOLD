from uuid import UUID
from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.users import UserResponse


class NewChoreConfirmationSummary(BaseModel):
    id: UUID
    user: UserResponse
    status: StatusConfirmENUM


class NewChoreConfirmationSetStatus(BaseModel):
    status: StatusConfirmENUM