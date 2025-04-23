from pydantic import BaseModel

from chores_completions.schemas import ChoreCompletionSchema
from chores_confirmations.schemas import ChoreConfirmationSummarySchema


class ChoreCompletionDetailSchema(BaseModel):
    chore_completion: ChoreCompletionSchema
    confirmed_by: list[ChoreConfirmationSummarySchema | None]