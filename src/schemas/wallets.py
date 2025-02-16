import uuid
from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import datetime


class ShowWallet(BaseModel):
    id: uuid.UUID
    balance: Decimal


class MoneyTransfer(BaseModel):
    to_user_id: uuid.UUID
    count: Decimal

    @field_validator('count')
    def check_age(cls, value):
        if value <= 0:
            raise ValueError('Error')
        return value
    

class CoinTransactionLog(BaseModel):
    transaction_type: str
    message: str
    transaction_with_user_id: uuid.UUID
    other_user_username: str
    other_user_name: str
    other_user_surname: str
    datetime: datetime
    coins: Decimal