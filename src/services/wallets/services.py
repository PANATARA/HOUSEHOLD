from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from core.constants import WalletTransactionENUM
from core.exceptions import NoSuchUserFoundInThefamily, NotEnoughCoins
from core.services import BaseService
from db.dals.chores import AsyncChoreDAL
from db.dals.wallets import AsyncTransactionLogDAL, AsyncWalletDAL
from db.models.chore import ChoreLog
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
class CoinsTransferService(BaseService):
    """
    Service for transferring coins between two users of the same family
    """
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
            user_id=self.from_user.id, amount=self.count
        )
        if result is None:
            raise NotEnoughCoins()

    async def _add_coins(self, wallet_dal: AsyncWalletDAL):
        await wallet_dal.add_balance(user_id=self.to_user.id, amount=self.count)

    async def _create_transaction_log(self):
        fields = {
            "description": self.message,
            "transaction_type": WalletTransactionENUM.transfer.value,
            "coins": self.count,
            "from_user_id": self.from_user.id,
            "to_user_id": self.to_user.id,
        }
        transaction_log_dal = AsyncTransactionLogDAL(self.db_session)
        return await transaction_log_dal.create(fields=fields)

    async def validate(self):
        if self.from_user.family_id != self.to_user.family_id:
            raise NoSuchUserFoundInThefamily()


@dataclass
class CoinsCreditService(BaseService):
    """
    Service for accruing coins for completing chore
    """

    chorelog: ChoreLog
    message: str
    db_session: AsyncSession

    async def execute(self) -> TransactionLog | None:
        user_id = self.chorelog.completed_by_id
        amount = await AsyncChoreDAL(self.db_session).get_chore_valutation(
            self.chorelog.chore_id
        )
        await self._add_coins(user_id, amount)
        transaction = await self._create_transaction_log(user_id, amount)
        return transaction
    
    async def _add_coins(self, user_id: UUID, amount: Decimal):
        wallet_dal = AsyncWalletDAL(self.db_session)
        await wallet_dal.add_balance(user_id=self.to_user.id, amount=self.count)

    async def _create_transaction_log(self, user_id: UUID, amount: Decimal):
        fields = {
            "description": self.message,
            "transaction_type": WalletTransactionENUM.income.value,
            "coins": amount,
            "to_user_id": user_id,
            "chore_log_id": self.chorelog.id,
        }
        transaction_log_dal = AsyncTransactionLogDAL(self.db_session)
        return await transaction_log_dal.create(fields=fields)
