from uuid import UUID
from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.users import UserSummarySchema


class NewChoreConfirmationSummary(BaseModel):
    id: UUID
    user: UserSummarySchema
    status: StatusConfirmENUM


class NewChoreConfirmationSetStatus(BaseModel):
    status: StatusConfirmENUM