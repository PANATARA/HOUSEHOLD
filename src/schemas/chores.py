from uuid import UUID
from pydantic import BaseModel

class TunedModel(BaseModel):
    class Config:
        """tells pydantic to convert even non dict obj to json"""

        from_attributes = True

class ChoreCreate(BaseModel):
    name: str
    description: str
    icon: str
    valuation: int


class ChoreShow(TunedModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: int


class ChoresResponse(BaseModel):
    chores: list[ChoreShow]

    class Config:
        orm_mode = True
        from_attributes = True 

