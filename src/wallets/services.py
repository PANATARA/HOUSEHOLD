from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import ChoreRepository
from config import TRANSFER_RATE
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from core.exceptions.wallets import NotEnoughCoins
from core.services import BaseService
from families.repository import FamilyRepository
from planned_chores.models import PlannedChore, QuickPlannedChore
from users.models import User
from users.repository import UserRepository
from wallets.models import PeerTransaction, RewardTransaction, Wallet
from wallets.repository import (
    PeerTransactionDAL,
    RewardTransactionDAL,
    WalletRepository,
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
class AwardService(BaseService[RewardTransaction]):
    planned_chore: PlannedChore
    message: str
    db_session: AsyncSession
    amount_multiplier: int = 1

    async def process(self) -> RewardTransaction:
        user_id = self.planned_chore.completed_by_id
        if user_id is None:
            raise ValueError("completed_by_id is None")

        chore = await ChoreRepository(self.db_session).get_by_id(
            self.planned_chore.chore_id
        )

        amount = chore.valuation * self.amount_multiplier

        await self._change_coins(user_id, amount)

        transaction = await self._create_transaction_log(
            user_id=user_id,
            amount=amount,
        )

        await self._change_experience(
            user_id=user_id,
            family_id=self.planned_chore.family_id,
            amount=amount,
        )

        return transaction

    async def _change_coins(self, user_id: UUID, amount: int) -> None:
        await WalletRepository(self.db_session).add_balance(user_id, amount)

    async def _create_transaction_log(
        self, user_id: UUID, amount: int
    ) -> RewardTransaction:
        transaction = RewardTransaction(
            detail=self.message,
            coins=amount,
            to_user_id=user_id,
            planned_chore_id=self.planned_chore.id,
            transaction_type=RewardTransactionENUM.reward_for_chore,
        )

        return await RewardTransactionDAL(self.db_session).create(transaction)

    async def _change_experience(
        self,
        user_id: UUID,
        family_id: UUID,
        amount: int,
    ) -> None:
        await UserRepository(self.db_session).increment_experience(user_id, amount)
        await FamilyRepository(self.db_session).increment_experience(family_id, amount)


@dataclass
class QuickAwardService(BaseService[RewardTransaction]):
    quick_chore: QuickPlannedChore
    message: str
    db_session: AsyncSession
    amount_multiplier: int = 1

    async def process(self) -> RewardTransaction:
        user_id = self.quick_chore.completed_by_id
        if user_id is None:
            raise ValueError("completed_by_id is None")

        # valuation берём напрямую из модели — не нужен ChoreRepository
        amount = self.quick_chore.valuation * self.amount_multiplier

        await self._change_coins(user_id, amount)
        transaction = await self._create_transaction_log(user_id, amount)
        await self._change_experience(
            user_id=user_id,
            family_id=self.quick_chore.family_id,
            amount=amount,
        )
        return transaction

    async def _change_coins(self, user_id: UUID, amount: int) -> None:
        await WalletRepository(self.db_session).add_balance(user_id, amount)

    async def _create_transaction_log(
        self, user_id: UUID, amount: int
    ) -> RewardTransaction:
        transaction = RewardTransaction(
            detail=self.message,
            coins=amount,
            to_user_id=user_id,
            planned_chore_id=None,
            transaction_type=RewardTransactionENUM.reward_for_chore,
        )
        return await RewardTransactionDAL(self.db_session).create(transaction)

    async def _change_experience(
        self,
        user_id: UUID,
        family_id: UUID,
        amount: int,
    ) -> None:
        await UserRepository(self.db_session).increment_experience(user_id, amount)
        await FamilyRepository(self.db_session).increment_experience(family_id, amount)
