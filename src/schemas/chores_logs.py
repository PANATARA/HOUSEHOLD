from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from schemas.chores import ChoreShow
from schemas.users import UserResponse

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
