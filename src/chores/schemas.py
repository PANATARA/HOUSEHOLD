from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChoreCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str = Field(default="material-symbols:cleaning-services-rounded", max_length=100)
    icon_color: str = Field(default="#ffffff", max_length=50)
    icon_bg: str = Field(default="linear-gradient(135deg, #8a7f6e 0%, #6b5f50 100%)", max_length=200)
    valuation: int = Field(default=10, ge=0, le=100000)


class ChoreUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=100)
    icon_color: str | None = Field(default=None, max_length=50)
    icon_bg: str | None = Field(default=None, max_length=200)
    valuation: int | None = Field(default=None, ge=0, le=100000)


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
