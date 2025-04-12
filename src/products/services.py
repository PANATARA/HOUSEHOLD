from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PeerTransactionENUM
from core.services import BaseService
from core.validators import validate_product_is_active, validate_user_can_buy_product
from products.models import Product
from products.repository import AsyncProductDAL
from users.models import User
from users.repository import AsyncUserDAL
from wallets.schemas import CreatePeerTransactionSchema
from wallets.services import PeerTransactionService


@dataclass
class PurchaseService(BaseService):
    product: Product
    user: User
    db_session: AsyncSession

    async def process(self):
        data = CreatePeerTransactionSchema(
            detail="message",
            coins=self.product.price,
        )
        from_user = await AsyncUserDAL(self.db_session).get_by_id(
            self.product.seller_id
        )
        peer_transaction_service = PeerTransactionService(
            to_user=self.user,
            from_user=from_user,
            product=self.product,
            data=data,
            transaction_type=PeerTransactionENUM.purchase,
            db_session=self.db_session,
        )
        transaction_log = await peer_transaction_service.run_process()
        await self._change_product_activity()

        return transaction_log

    async def _change_product_activity(self) -> None:
        product_dal = AsyncProductDAL(self.db_session)
        await product_dal.update(object_id=self.product.id, fields={"is_active": False})

    def get_validators(self):
        return [
            lambda: validate_product_is_active(self.product),
            lambda: validate_user_can_buy_product(self.product, self.user)
        ]
