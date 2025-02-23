from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from schemas.chores import ChoreShow
from schemas.users import UserResponse
from schemas.wallets import CoinTransactionLog

class ChoreLogCreate(BaseModel):
    chore_id: UUID
    message: str


class ChoreLogConfirm(BaseModel):
    message: str
    status: int


class ChoreLogShow(BaseModel):
    id: UUID
    chore: ChoreShow
    completed_by: UserResponse
    completed_at: datetime
    message: str
    status: str


class ChoreConfirmation(BaseModel):
    id: UUID
    chorelog: ChoreLogShow
    status: str



class ChoreLogConfirmation(BaseModel):
    id: UUID
    user: UserResponse
    status: str

class ChoreLogDetailShow(BaseModel):
    id: UUID
    chore: ChoreShow
    completed_by: UserResponse
    completed_at: datetime
    # transaction: CoinTransactionLog
    message: str
    status: str
    confirmed_by: list[ChoreLogConfirmation]
