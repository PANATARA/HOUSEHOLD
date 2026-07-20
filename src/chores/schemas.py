from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChoreCreateSchema(BaseModel):
    name: str = Field(max_length=32)
    description: str = Field(max_length=128)
    icon: str
    icon_color: str
    icon_bg: str
    valuation: int


class ChoreUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=128)
    icon: str | None = None
    icon_color: str | None = None
    icon_bg: str | None = None
    valuation: int | None = None


class ChoreResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    icon: str
    icon_color: str
    icon_bg: str
    valuation: int
    default_chore_id: UUID | None


class ChoresListResponseSchema(BaseModel):
    chores: list[ChoreResponseSchema]


class DefaultChoreResponseSchema(BaseModel):
    id: UUID
    name: str
    description: str | None
    icon: str
    icon_color: str
    icon_bg: str
    valuation: int
    order: int


class ChoresFromDefaultsSchema(BaseModel):
    default_chore_ids: list[UUID]
    language: str = "ru"
