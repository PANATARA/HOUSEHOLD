from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.chores.chores import ChoreSchema
from schemas.chores.chores_completions import (
    ChoreCompletionLiteSchema,
    ChoreCompletionSchema,
)
from schemas.chores.chores_confirmations import NewChoreConfirmationSummary
from schemas.users import UserSummarySchema


class NewChoreCompletionDetail(BaseModel):
    id: UUID
    chore: ChoreSchema
    completed_by: UserSummarySchema
    completed_at: datetime
    status: str
    message: str
    confirmed_by: list[NewChoreConfirmationSummary | None]


class NewChoreConfirmationDetail(BaseModel):
    """Only for a specific user"""

    id: UUID
    chore_completion: ChoreCompletionSchema
    status: StatusConfirmENUM


class NewChoreDetailMax(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: Decimal
    created_at: datetime
    chores_completion: list[ChoreCompletionLiteSchema | None]
