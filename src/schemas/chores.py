from pydantic import BaseModel

class ChoreCreate(BaseModel):
    name: str
    description: str
    icon: str
    valuation: int
