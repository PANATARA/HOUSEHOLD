from uuid import UUID

from pydantic import BaseModel

from chores_completions.schemas import ChoreCompletionSchema
from core.constants import StatusConfirmENUM


class ChoreConfirmationDetailSchema(BaseModel):
    """Only for a specific user"""

    id: UUID
    chore_completion: ChoreCompletionSchema
    status: StatusConfirmENUM
