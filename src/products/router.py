from decimal import Decimal
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions.products import ProductNotFoundError
from core.exceptions.wallets import NotEnoughCoins
from core.get_avatars import update_user_avatars
from core.permissions import IsAuthenicatedPermission, ProductPermission
from core.query_depends import get_pagination_params
from database_connection import get_db
from products.models import Product
from products.repository import AsyncProductDAL, ProductDataService
from products.schemas import (
    CreateNewProductSchema,
    ProductFullSchema,
    ProductWithSellerSchema,
)
from products.services import PurchaseService
from users.models import User

logger = getLogger(__name__)

router = APIRouter()


# Create new product
@router.post(path="", summary="Create a new product", tags=["Products"])
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
        new_product = Product(**fields)
        new_product = await product_dal.create(new_product)
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
@router.get(
    path="/users", summary="Get a list of user's active products", tags=["Products"]
)
async def get_user_products(
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ProductFullSchema]:
    async with async_session.begin():
        product_data = ProductDataService(async_session)
        result_response = await product_data.get_user_active_products(current_user.id)
    return result_response


@router.get(
    path="/family",
    summary="Get a list of active products for the user's family, with pagination",
    tags=["Products"],
)
async def get_family_active_products(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    current_user: User = Depends(IsAuthenicatedPermission()),
    async_session: AsyncSession = Depends(get_db),
) -> list[ProductWithSellerSchema]:
    async with async_session.begin():
        offset, limit = pagination
        product_data = ProductDataService(async_session)
        family_id = current_user.family_id
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        result = await product_data.get_family_active_products(family_id, limit, offset)
        await update_user_avatars(result)
        return result


@router.post(
    path="/buy/{product_id}",
    summary="Buy a product from the active product list",
    tags=["Products"],
)
async def buy_active_products(
    product_id: UUID,
    current_user: User = Depends(ProductPermission()),
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
        except NotEnoughCoins:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
