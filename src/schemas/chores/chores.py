from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ChoreCreateSchema(BaseModel):
    name: str = Field(max_length=32)
    description: str = Field(max_length=128)
    icon: str = Field(max_length=64)
    valuation: Decimal


class ChoreSchema(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: Decimal
