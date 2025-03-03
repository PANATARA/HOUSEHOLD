from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from core.exceptions import NoSuchUserFoundInThefamily, NotEnoughCoins
from core.services import BaseService
from db.dals.chores import AsyncChoreDAL
from db.dals.coins_transactions import PeerTransactionDAL, RewardTransactionDAL
from db.dals.wallets import AsyncWalletDAL
from db.models.chore import ChoreCompletion
from db.models.user import User
from db.models.wallet import PeerTransaction, RewardTransaction, Wallet
from schemas.coins_transactions import CreateRewardTransaction, CreateTransferTransaction


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

    async def execute(self) -> PeerTransaction | None:
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
        data = CreateTransferTransaction(
            detail=self.message,
            coins=self.count,
            to_user_id=self.to_user.id,
            from_user_id=self.from_user.id,
        )
        transaction_log_dal = PeerTransactionDAL(self.db_session)
        return await transaction_log_dal.create_transfer_transaction(data=data)

    async def validate(self):
        if self.from_user.family_id != self.to_user.family_id:
            raise NoSuchUserFoundInThefamily()


@dataclass
class CoinsRewardService(BaseService):
    """
    Service for accruing coins for completing chore
    """

    chore_completion: ChoreCompletion
    message: str
    db_session: AsyncSession

    async def execute(self) -> RewardTransaction | None:
        user_id = self.chore_completion.completed_by_id
        amount = await AsyncChoreDAL(self.db_session).get_chore_valutation(
            self.chore_completion.chore_id
        )
        await self._add_coins(user_id, amount)
        transaction = await self._create_transaction_log(user_id, amount)
        return transaction
    
    async def _add_coins(self, user_id: UUID, amount: Decimal):
        wallet_dal = AsyncWalletDAL(self.db_session)
        await wallet_dal.add_balance(user_id=user_id, amount=amount)

    async def _create_transaction_log(self, user_id: UUID, amount: Decimal):
        data = CreateRewardTransaction(
            detail = self.message,
            coins = amount,
            to_user_id =  user_id,
            chore_completion_id =  self.chore_completion.id,
        )
        transaction_log_dal = RewardTransactionDAL(self.db_session)
        return await transaction_log_dal.create_reward_for_chore_transaction(data=data)
