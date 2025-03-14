from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from decimal import Decimal

from schemas.chores.chores_completions import NewChoreCompletionSummaryLite
from schemas.products import ProductLiteSchema
from schemas.users import UserSummarySchema


class ShowWalletBalance(BaseModel):
    id: UUID
    balance: Decimal


class MoneyTransfer(BaseModel):
    to_user_id: UUID
    count: Decimal

    @field_validator('count')
    def check_count(cls, value):
        if value <= 0:
            raise ValueError('Error')
        return value


class NewWalletTransaction(BaseModel):
    id: UUID
    detail: str
    coins: Decimal
    transaction_type: str
    transaction_direction: str
    created_at: datetime
    other_user: UserSummarySchema | None
    product: ProductLiteSchema | None
    chore_completion: NewChoreCompletionSummaryLite | None
