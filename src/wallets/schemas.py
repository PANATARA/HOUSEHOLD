from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

from chores_completions.schemas import ChoreCompletionSummaryLiteSchema
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from products.schemas import ProductFullSchema
from users.schemas import UserSummarySchema


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


class CreatePeerTransactionSchema(BaseModel):
    detail: str
    coins: Decimal


class CreateRewardTransactionSchema(BaseModel):
    detail: str
    coins: Decimal
    to_user_id: UUID
    chore_completion_id: UUID


class BaseWalletTransaction(BaseModel):
    id: UUID
    detail: str
    coins: Decimal
    created_at: datetime
    transaction_direction: Literal["incoming", "outgoing"]


class PurchaseTransactionSchema(BaseWalletTransaction):
    transaction_type: str = PeerTransactionENUM.purchase.value
    other_user: UserSummarySchema
    product: ProductFullSchema


class TransferTransactionSchema(BaseWalletTransaction):
    transaction_type: str = PeerTransactionENUM.transfer.value
    other_user: UserSummarySchema


class RewardTransactionSchema(BaseWalletTransaction):
    transaction_type: str = RewardTransactionENUM.reward_for_chore.value
    chore_completion: ChoreCompletionSummaryLiteSchema


class UnionTransactionsSchema(BaseModel):
    transactions: list[
        PurchaseTransactionSchema | TransferTransactionSchema | RewardTransactionSchema
    ]
