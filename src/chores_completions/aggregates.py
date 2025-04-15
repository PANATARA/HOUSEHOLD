from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from chores.schemas import ChoreSchema
from chores_confirmations.schemas import ChoreConfirmationSummarySchema
from users.schemas import UserSummarySchema


class ChoreCompletionDetailSchema(BaseModel):
    id: UUID
    chore: ChoreSchema
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str
    confirmed_by: list[ChoreConfirmationSummarySchema | None]