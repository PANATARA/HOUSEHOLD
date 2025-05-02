from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from users.schemas import UserResponseSchema


class ProductBaseSchema(BaseModel):
    name: str
    description: str
    icon: str
    price: Decimal


class CreateNewProductSchema(ProductBaseSchema):
    """Schema for creating a new product"""


class ProductFullSchema(ProductBaseSchema):
    id: UUID
    is_active: bool
    created_at: datetime


class ProductWithSellerSchema(ProductFullSchema):
    seller: UserResponseSchema
