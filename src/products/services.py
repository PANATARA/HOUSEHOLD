from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from config import PURCHASE_RATE
from core.enums import PeerTransactionENUM
from core.services import BaseService
from core.validators import validate_product_is_active, validate_user_can_buy_product
from products.models import Product
from products.repository import ProductRepository
from users.models import User
from wallets.models import PeerTransaction
from wallets.repository import PeerTransactionDAL
from wallets.services import coin_exchange


@dataclass
class PurchaseService(BaseService[PeerTransaction]):
    product: Product
    user: User
    db_session: AsyncSession

    async def process(self):
        transaction = await self._create_transaction_log()
        await self._change_product_activity()
        await coin_exchange(
            to_user_id=self.product.seller_id,
            from_user_id=self.user.id,
            coins=self.product.price,
            rate=PURCHASE_RATE,
            db_session=self.db_session,
        )
        return transaction

    async def _change_product_activity(self) -> None:
        product_dal = ProductRepository(self.db_session)
        self.product.is_active = False
        await product_dal.update(self.product)

    async def _create_transaction_log(self):
        transaction = PeerTransaction(
            detail="detail",
            coins=self.product.price,
            to_user_id=self.product.seller_id,
            from_user_id=self.user.id,
            product_id=self.product.id,
            transaction_type=PeerTransactionENUM.purchase,
        )
        transaction_log_dal = PeerTransactionDAL(self.db_session)
        return await transaction_log_dal.create(transaction)

    def get_validators(self):
        return [
            lambda: validate_product_is_active(self.product),
            lambda: validate_user_can_buy_product(self.product, self.user),
        ]
