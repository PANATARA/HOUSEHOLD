from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_dals import BaseDals
from products.models import Product
from products.schemas import ProductFullSchema, ProductWithSellerSchema
from users.models import User


class AsyncProductDAL(BaseDals[Product]):

    model = Product


@dataclass
class ProductDataService:
    """Return product's pydantic models"""

    db_session: AsyncSession

    async def get_user_active_products(self, user_id: UUID) -> list[ProductFullSchema]:
        """Returns a pydantic model of the product"""
        query = select(
            Product.id,
            Product.name,
            Product.description,
            Product.icon,
            Product.price,
            Product.is_active,
            Product.created_at,
        ).where(and_(Product.seller_id == user_id, Product.is_active))
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        return [ProductFullSchema.model_validate(product) for product in raw_data]

    async def get_family_active_products(
        self, family_id: UUID, limit: int, offset: int
    ) -> list[ProductWithSellerSchema]:
        """Returns a pydantic model of the product"""
        query = (
            select(
                Product.id,
                Product.name,
                Product.description,
                Product.icon,
                Product.price,
                Product.is_active,
                Product.created_at,
                func.json_build_object(
                    "id",
                    User.id,
                    "username",
                    User.username,
                    "name",
                    User.name,
                    "surname",
                    User.surname,
                ).label("seller"),
            )
            .where(
                and_(
                    Product.family_id == family_id,
                    Product.is_active,
                )
            )
            .join(User, User.id == Product.seller_id)
            .limit(limit)
            .offset(offset)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        return [ProductWithSellerSchema.model_validate(product) for product in raw_data]
