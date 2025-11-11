from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from users.schemas import UserResponseSchema


class ProductBaseSchema(BaseModel):
    name: str
    description: str
    icon: str
    price: int


class CreateNewProductSchema(ProductBaseSchema):
    """Schema for creating a new product"""


class ProductFullSchema(ProductBaseSchema):
    id: UUID
    is_active: bool
    created_at: datetime
    avatar_version: int | None


class ProductWithSellerSchema(ProductFullSchema):
    seller: UserResponseSchema
