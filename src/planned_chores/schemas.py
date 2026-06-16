from datetime import date
from uuid import UUID

from pydantic import BaseModel


class PlannedChoreCreateSchema(BaseModel):
    assigned_to_id: UUID | None
    due_date: date
    message: str
