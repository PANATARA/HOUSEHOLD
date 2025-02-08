from uuid import UUID
from pydantic import BaseModel

from schemas.chores import ChoreShow
from schemas.users import ShowUser

class ChoreLogCreate(BaseModel):
    chore_id: UUID
    message: str


class ChoreLogShow(BaseModel):
    id: UUID
    chore: ChoreShow
    completed_by: ShowUser
    status: str