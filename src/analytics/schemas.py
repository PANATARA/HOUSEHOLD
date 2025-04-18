from datetime import date
from pydantic import BaseModel


class ChoreAnalyticSchema(BaseModel):
    family_id: str
    chore_id: str
    user_id: str
    completion_date: date
