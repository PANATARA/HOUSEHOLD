from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class _Transaction(BaseModel):
    detail: str
    coins: Decimal
    to_user_id: UUID


class CreatePurchaseTransaction(_Transaction):
    product_id: UUID


class CreateTransferTransaction(_Transaction):
    from_user_id: UUID


class CreateRewardTransaction(_Transaction):
    chore_completion_id: UUID
