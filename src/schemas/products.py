from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel

from schemas.users import UserSummarySchema


class ProductLiteSchema(BaseModel):
    id: UUID
    name: str
    icon: str


class CreateNewProductSchema(BaseModel):
    name: str
    description: str
    icon: str
    price: Decimal


class ProductFullSchema(BaseModel):
    id: UUID
    name: str
    description: str
    icon: str
    price: Decimal
    is_active: bool
    created_at: datetime


class ProductWithSellerSchema(ProductFullSchema):
    seller: UserSummarySchema