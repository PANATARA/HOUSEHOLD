from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from core.constants import TransactionTypeEnum
from core.exceptions import NoSuchUserFoundInThefamily, NotEnoughCoins
from core.services import BaseService
from db.dals.wallets import AsyncTransactionLogDAL, AsyncWalletDAL
from db.models.user import User
from db.models.wallet import TransactionLog, Wallet


@dataclass
class WalletCreatorService(BaseService):
    """Create and return a new User's wallet"""
    user: User
    db_session: AsyncSession

    async def execute(self) -> Wallet:
        wallet = await self._create_wallet()
        return wallet
    
    async def _create_wallet(self) -> Wallet:
        wallet_dal = AsyncWalletDAL(self.db_session)
        wallet = await wallet_dal.create({"user_id": self.user.id})
        return wallet
    
    async def validate(self):
        wallet_dal = AsyncWalletDAL(self.db_session)
        if await wallet_dal.exist_wallet_user(self.user.id):
            await wallet_dal.delete_wallet_user(self.user.id)

@dataclass
class MoneyTransferService(BaseService):
    from_user: User
    to_user: User
    count: Decimal
    message: str
    db_session: AsyncSession

    async def execute(self) -> TransactionLog | None:
        wallet_dal = AsyncWalletDAL(self.db_session)
        await self._take_coins(wallet_dal)
        await self._add_coins(wallet_dal)
        transaction_log = await self._create_transaction_log()

        return transaction_log
    
    async def _take_coins(self, wallet_dal: AsyncWalletDAL) -> Decimal | None:
        result = await wallet_dal.deduct_balance(
            user_id=self.from_user.id, 
            amount=self.count
        )
        if result is None:
            raise NotEnoughCoins()

    async def _add_coins(self, wallet_dal: AsyncWalletDAL):
        await wallet_dal.add_balance(
            user_id=self.to_user.id, 
            amount=self.count
        )
    
    async def _create_transaction_log(self):
        fields = {
            "description": self.message,
            "transaction_type": TransactionTypeEnum.transfer.value,
            "coins": self.count,
            "from_user_id": self.from_user.id,
            "to_user_id": self.to_user.id,
        }
        transaction_log_dal = AsyncTransactionLogDAL(self.db_session)
        return await transaction_log_dal.create(fields=fields)


    async def validate(self):
        if self.from_user.family_id != self.to_user.family_id:
            raise NoSuchUserFoundInThefamily()
