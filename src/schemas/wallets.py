from uuid import UUID
from pydantic import BaseModel, field_validator
from decimal import Decimal

from schemas.chores_completions import NewChoreCompletionSummaryLite
from schemas.users import UserResponse


class ShowWalletBalance(BaseModel):
    id: UUID
    balance: Decimal


class MoneyTransfer(BaseModel):
    to_user_id: UUID
    count: Decimal

    @field_validator('count')
    def check_age(cls, value):
        if value <= 0:
            raise ValueError('Error')
        return value


class WalletTransactionLog(BaseModel):
    description: str
    transaction_type: str
    coins: Decimal
    user: UserResponse | None
    # product: ProductModel
    chore_completion: NewChoreCompletionSummaryLite | None 