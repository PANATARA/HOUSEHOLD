from uuid import UUID

from pydantic import BaseModel, Field


class ChoreCreateSchema(BaseModel):
    name: str = Field(max_length=32)
    description: str = Field(max_length=128)
    icon: str = Field(max_length=64)
    valuation: int


class ChoreUpdateSchema(BaseModel):
    name: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=128)
    icon: str | None = Field(default=None, max_length=64)
    valuation: int | None = None


class ChoreResponseSchema(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    valuation: int


class ChoresListResponseSchema(BaseModel):
    chores: list[ChoreResponseSchema]

    def sort_chores_by_id(self, chores_ids: list[UUID]):
        chores_map = {chore.id: chore for chore in self.chores}

        sorted_chores = [
            chores_map.pop(chore_id)
            for chore_id in chores_ids
            if chore_id in chores_map
        ]
        sorted_chores.extend(chores_map.values())
        self.chores = sorted_chores
