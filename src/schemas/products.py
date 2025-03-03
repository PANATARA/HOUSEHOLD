from uuid import UUID
from pydantic import BaseModel


class ProductSchema(BaseModel):
    id: UUID
    name: str
    icon: str