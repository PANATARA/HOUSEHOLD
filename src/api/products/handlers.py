from decimal import Decimal
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.permissions import IsAuthenicatedPermission
from core.exceptions.products import ProductNotFoundError
from db.dals.products import AsyncProductDAL
from db.models.user import User
from db.session import get_db
from schemas.products import (
    CreateNewProductSchema,
    ProductFullSchema,
    ProductWithSellerSchema,
)
from services.products.data import ProductDataService
from services.products.services import PurchaseService

logger = getLogger(__name__)

product_router = APIRouter()


# Create new product
@product_router.post(path="")
async def create_product(
    body: CreateNewProductSchema,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> ProductFullSchema:
    async with async_session.begin():
        product_dal = AsyncProductDAL(async_session)
        fields = body.model_dump()
        fields.update(
            {"seller_id": current_user.id, "family_id": current_user.family_id}
        )
        new_product = await product_dal.create(fields)
        return ProductFullSchema(
            id=new_product.id,
            name=new_product.name,
            description=new_product.description,
            icon=new_product.icon,
            price=Decimal(new_product.price),
            is_active=new_product.is_active,
            created_at=new_product.created_at,
        )


# Get a list of user's products
@product_router.get(path="/users")
async def get_user_products(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ProductFullSchema]:
    async with async_session.begin():
        product_data = ProductDataService(async_session)
        return await product_data.get_user_active_products(current_user.id)


# Get a list of active products in the family
@product_router.get(path="/family")
async def get_family_active_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=20),
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ProductWithSellerSchema]:
    async with async_session.begin():
        offset = (page - 1) * limit
        product_data = ProductDataService(async_session)
        family_id = current_user.family_id
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return await product_data.get_family_active_products(family_id, limit, offset)


# Buy a product
@product_router.get(path="/buy/{product_id}")
async def buy_active_products(
    product_id: UUID,
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> Response:
    async with async_session.begin():
        try:
            product = await AsyncProductDAL(async_session).get_by_id(product_id)
            if not product:
                raise ProductNotFoundError

            service = PurchaseService(
                product=product, user=current_user, db_session=async_session
            )
            await service.run_process()
        except ProductNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
