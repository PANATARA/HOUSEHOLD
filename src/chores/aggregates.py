from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from chores_completions.schemas import ChoreCompletionLiteSchema


class ChoreDetailSchema(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: Decimal
    created_at: datetime
    chores_completion: list[ChoreCompletionLiteSchema | None]