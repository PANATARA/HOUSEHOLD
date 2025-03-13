from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class NewChoreCreate(BaseModel):
    name: str = Field(max_length=32)
    description: str = Field(max_length=128)
    icon: str = Field(max_length=64)
    valuation: Decimal


class NewChoreSummary(BaseModel):
    id: UUID
    name: str
    icon: str
    valuation: Decimal


class NewChoreDetail(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: Decimal
    created_at: datetime
