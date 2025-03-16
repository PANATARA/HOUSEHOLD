from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from schemas.chores.chores_completions import ChoreCompletionSummaryLiteSchema
from schemas.products import ProductFullSchema
from schemas.users import UserSummarySchema


class WalletBalanceSchema(BaseModel):
    id: UUID
    balance: Decimal


class MoneyTransferSchema(BaseModel):
    to_user_id: UUID
    count: Decimal

    @field_validator("count")
    def check_count(cls, value):
        if value <= 0:
            raise ValueError("Error")
        return value


class WalletTransactionSchema(BaseModel):
    id: UUID
    detail: str
    coins: Decimal
    transaction_type: str
    transaction_direction: str
    created_at: datetime
    other_user: UserSummarySchema | None
    product: ProductFullSchema | None
    chore_completion: ChoreCompletionSummaryLiteSchema | None
