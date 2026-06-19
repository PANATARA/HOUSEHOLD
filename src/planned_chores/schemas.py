from datetime import date
from uuid import UUID

from pydantic import BaseModel

from chores.schemas import ChoreResponseSchema
from users.schemas import UserResponseSchema


class PlannedChoreCreateSchema(BaseModel):
    assigned_to_id: UUID | None
    due_date: date
    message: str


class PlannedChoreResponseSchema(BaseModel):
    id: UUID
    chore: ChoreResponseSchema
    completed_by: UserResponseSchema | None = None
    assigned_to: UserResponseSchema | None = None
    due_date: date
    message: str

    model_config = {"from_attributes": True}
