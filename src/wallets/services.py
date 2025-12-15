from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import ChoreRepository
from chores_completions.models import ChoreCompletion
from config import TRANSFER_RATE
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from core.exceptions.wallets import NotEnoughCoins
from core.services import BaseService
from core.validators import (
    validate_chore_completion_is_approved,
)
from families.repository import FamilyRepository
from users.models import User
from users.repository import UserRepository
from wallets.models import PeerTransaction, RewardTransaction, Wallet
from wallets.repository import (
    WalletRepository,
    PeerTransactionDAL,
    RewardTransactionDAL,
)


async def coin_exchange(
    to_user_id: UUID,
    from_user_id: UUID,
    coins: int,
    rate: Decimal,
    db_session: AsyncSession,
):
    wallet_dal = WalletRepository(db_session)
    from_wallet = await wallet_dal.get_by_user_id(from_user_id)
    if not from_wallet:
        raise ValueError(f"Wallet for user {from_user_id} not found")
    if from_wallet.balance < coins:
        raise NotEnoughCoins()
    from_wallet.balance -= coins
    await wallet_dal.update(from_wallet)

    to_wallet = await wallet_dal.get_by_user_id(to_user_id)
    if not to_wallet:
        raise ValueError(f"Wallet for user {to_user_id} not found")
    amount_to_add = int(coins * rate)
    to_wallet.balance += amount_to_add
    await wallet_dal.update(to_wallet)


@dataclass
class WalletCreatorService(BaseService[Wallet]):
    """
    Creates a new user wallet and deletes the old one if it exists
    """

    user: User
    db_session: AsyncSession

    async def process(self) -> Wallet:
        wallet = await self._create_wallet()
        return wallet

    async def _create_wallet(self) -> Wallet:
        wallet_dal = WalletRepository(self.db_session)
        wallet = await wallet_dal.create(Wallet(user_id=self.user.id))
        return wallet


@dataclass
class CoinsTransferService(BaseService[PeerTransaction | None]):
    """
    Service for transferring coins between two users of the same family
    """

    from_user: User
    to_user: User
    count: int
    message: str
    db_session: AsyncSession

    async def process(self) -> PeerTransaction:
        transaction = await self._create_transaction_log()
        await coin_exchange(
            to_user_id=self.to_user.id,
            from_user_id=self.from_user.id,
            coins=self.count,
            db_session=self.db_session,
            rate=TRANSFER_RATE,
        )
        return transaction

    async def _create_transaction_log(self):
        transaction = PeerTransaction(
            detail=self.message,
            coins=self.count,
            to_user_id=self.to_user.id,
            from_user_id=self.from_user.id,
            product_id=None,
            transaction_type=PeerTransactionENUM.transfer,
        )
        transaction_log_dal = PeerTransactionDAL(self.db_session)
        return await transaction_log_dal.create(transaction)


@dataclass
class CoinsRewardService(BaseService[RewardTransaction]):
    """
    Service for accruing coins for completing chore
    """

    chore_completion: ChoreCompletion
    message: str
    db_session: AsyncSession

    async def process(self) -> RewardTransaction:
        user_id = self.chore_completion.completed_by_id
        chore = await ChoreRepository(self.db_session).get_by_id(
            self.chore_completion.chore_id
        )
        await self._add_coins(user_id, chore.valuation)
        transaction = await self._create_transaction_log(user_id, chore.valuation)
        await self._add_experience(
            user_id, self.chore_completion.family_id, chore.valuation
        )
        return transaction

    async def _add_coins(self, user_id: UUID, amount: int):
        wallet_dal = WalletRepository(self.db_session)
        await wallet_dal.add_balance(user_id=user_id, amount=amount)

    async def _create_transaction_log(self, user_id: UUID, amount: int):
        transaction = RewardTransaction(
            detail=self.message,
            coins=amount,
            to_user_id=user_id,
            chore_completion_id=self.chore_completion.id,
            transaction_type=RewardTransactionENUM.reward_for_chore,
        )
        transaction_log_dal = RewardTransactionDAL(self.db_session)
        return await transaction_log_dal.create(transaction)

    async def _add_experience(self, user_id: UUID, family_id: UUID, amount: int):
        await UserRepository(self.db_session).increment_experience(user_id, amount)
        await FamilyRepository(self.db_session).increment_experience(family_id, amount)

    def get_validators(self):
        return [lambda: validate_chore_completion_is_approved(self.chore_completion)]
