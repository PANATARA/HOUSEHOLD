import uuid
from pydantic import BaseModel
from decimal import Decimal

from schemas.users import ShowUser

class ShowWallet(BaseModel):
    id: uuid.UUID
    balance: Decimal

class MoneyTransfer(BaseModel):
    to_user_id: uuid.UUID
    count: Decimal