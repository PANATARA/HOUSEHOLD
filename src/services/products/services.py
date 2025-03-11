from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PeerTransactionENUM
from core.exceptions import DebugError, ProductNotFoundError
from core.services import BaseService
from db.dals.products import AsyncProductDAL
from db.dals.users import AsyncUserDAL
from db.models.product import Product
from db.models.user import User
from schemas.coins_transactions import CreatePeerTransaction
from services.wallets.services import PeerTransactionService


@dataclass
class PurchaseService(BaseService):
    product: Product 
    user: User
    db_session: AsyncSession

    async def process(self):
        data = CreatePeerTransaction(
            detail = "message",
            coins = self.product.price,
        )
        from_user = await AsyncUserDAL(self.db_session).get_by_id(self.product.seller_id)
        peer_transaction_service = PeerTransactionService(
            to_user = self.user,
            from_user = from_user,
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
        await product_dal.update(
            object_id=self.product.id, fields={"is_active": False} 
        )

    def validate(self):
        if not self.product.is_active:
            raise ProductNotFoundError
        if self.product.seller_id == self.user.id:
            raise DebugError