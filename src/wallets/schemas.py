from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

from chores.schemas import ChoreResponseSchema
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from products.schemas import ProductFullSchema
from users.schemas import UserResponseSchema


class WalletBalanceSchema(BaseModel):
    balance: Decimal


class MoneyTransferSchema(BaseModel):
    to_user_id: UUID
    count: Decimal

    @field_validator("count")
    def check_count(cls, value):
        if value <= 0:
            raise ValueError("Error")
        return value


class CreatePeerTransactionSchema(BaseModel):
    detail: str
    coins: Decimal
    transaction_type: PeerTransactionENUM


class BaseWalletTransaction(BaseModel):
    """ABSTRACT MODEL"""

    id: UUID
    detail: str
    coins: Decimal
    created_at: datetime
    transaction_direction: Literal["incoming", "outgoing"]


class PurchaseTransactionSchema(BaseWalletTransaction):
    transaction_type: str = PeerTransactionENUM.purchase.value
    other_user: UserResponseSchema
    product: ProductFullSchema


class TransferTransactionSchema(BaseWalletTransaction):
    transaction_type: str = PeerTransactionENUM.transfer.value
    other_user: UserResponseSchema


class RewardTransactionSchema(BaseWalletTransaction):
    class ChoreCompletionTransactionSchema(BaseModel):
        id: UUID
        chore: ChoreResponseSchema
        completed_at: datetime

    transaction_type: str = RewardTransactionENUM.reward_for_chore.value
    chore_completion: ChoreCompletionTransactionSchema


class UnionTransactionsSchema(BaseModel):
    transactions: list[
        PurchaseTransactionSchema | TransferTransactionSchema | RewardTransactionSchema
    ]
