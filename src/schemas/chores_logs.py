from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from core.constants import StatusConfirmENUM
from schemas.chores import ChoreShort, ChoreShow
from schemas.users import UserResponse

class ChoreCompletionCreate(BaseModel):
    chore_id: UUID
    message: str


class ChoreCompletionConfirm(BaseModel):
    message: str
    status: int


class ChoreCompletionShow(BaseModel):
    id: UUID
    chore: ChoreShow
    completed_by: UserResponse
    completed_at: datetime
    message: str
    status: str

class ChoreCompletionShort(BaseModel):
    id: UUID
    chore: ChoreShort
    completed_at: datetime

class ChoreConfirmation(BaseModel):
    id: UUID
    chore_completion: ChoreCompletionShow
    status: str


class ChoreCompletionConfirmationChangeStatus(BaseModel):
    status: StatusConfirmENUM

class ChoreCompletionConfirmation(BaseModel):
    id: UUID
    user: UserResponse
    status: str

class ChoreCompletionDetailShow(BaseModel):
    id: UUID
    chore: ChoreShow
    completed_by: UserResponse
    completed_at: datetime
    # transaction: CoinTransactionLog
    message: str
    status: str
    confirmed_by: list[ChoreCompletionConfirmation]
