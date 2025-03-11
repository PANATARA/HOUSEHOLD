from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class CreatePeerTransaction(BaseModel):
    detail: str
    coins: Decimal


class CreateRewardTransaction(BaseModel):
    detail: str
    coins: Decimal
    to_user_id: UUID
    chore_completion_id: UUID
