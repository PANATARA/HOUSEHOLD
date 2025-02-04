import uuid
from pydantic import BaseModel
from decimal import Decimal

class ShowWallet(BaseModel):
    id: uuid.UUID
    balance: Decimal
