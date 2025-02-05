import uuid
from pydantic import BaseModel
from decimal import Decimal

class ShowWallet(BaseModel):
    id: uuid.UUID
    balance: Decimal

class MoneyTransfer(BaseModel):
    to_user: uuid.UUID
    count: Decimal