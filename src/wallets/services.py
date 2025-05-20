from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from chores.repository import AsyncChoreDAL
from chores_completions.models import ChoreCompletion
from config import PURCHASE_RATE, TRANSFER_RATE
from core.enums import PeerTransactionENUM, RewardTransactionENUM
from core.exceptions.wallets import NotEnoughCoins
from core.services import BaseService
from core.validators import (
    validate_chore_completion_is_approved,
    validate_user_in_family,
)
from products.models import Product
from users.models import User
from wallets.models import PeerTransaction, RewardTransaction, Wallet
from wallets.repository import AsyncWalletDAL, PeerTransactionDAL, RewardTransactionDAL
from wallets.schemas import CreatePeerTransactionSchema


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
        wallet_dal = AsyncWalletDAL(self.db_session)
        wallet = await wallet_dal.create({"user_id": self.user.id})
        return wallet

    async def validate(self):
        wallet_dal = AsyncWalletDAL(self.db_session)
        if await wallet_dal.exist_wallet_user(self.user.id):
            await wallet_dal.delete_wallet_user(self.user.id)


@dataclass
class CoinsTransferService(BaseService[PeerTransaction | None]):
    """
    Service for transferring coins between two users of the same family
    """

    from_user: User
    to_user: User
    count: Decimal
    message: str
    db_session: AsyncSession

    async def process(self) -> PeerTransaction | None:
        data = CreatePeerTransactionSchema(
            detail=self.message,
            coins=self.count,
            transaction_type=PeerTransactionENUM.transfer,
        )
        peer_transaction_service = PeerTransactionService(
            to_user=self.to_user,
            from_user=self.from_user,
            data=data,
            db_session=self.db_session,
        )
        return await peer_transaction_service.run_process()

    def get_validators(self):
        return [lambda: validate_user_in_family(self.from_user, self.to_user.family_id)]


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
        transaction = RewardTransaction(
            detail=self.message,
            coins=amount,
            to_user_id=user_id,
            chore_completion_id=self.chore_completion.id,
            transaction_type = RewardTransactionENUM.reward_for_chore
        )
        transaction_log_dal = RewardTransactionDAL(self.db_session)
        return await transaction_log_dal.create(transaction)

    def get_validators(self):
        return [lambda: validate_chore_completion_is_approved(self.chore_completion)]


@dataclass
class PeerTransactionService(BaseService[PeerTransaction | None]):
    """
    Service for handling peer-to-peer transactions, including coin transfers and product buying

    This service is intended to be used by other services within the system.
    It should not be called directly by external requests or end-users.

    Attributes:
        to_user (User): The user receiving the transaction.
        from_user (User): The user sending the transaction.
        data (CreatePeerTransaction): The transaction details.
        transaction_type (PeerTransactionENUM): The type of the transaction (purchase or transfer).
        db_session (AsyncSession): The database session for executing queries.
        product (Product | None): The product associated with the transaction, if any.
    """

    to_user: User
    from_user: User
    data: CreatePeerTransactionSchema
    db_session: AsyncSession
    product: Product | None = None

    async def process(self) -> PeerTransaction:
        await self._take_coins()
        await self._add_coins()
        transaction_log = await self._create_transaction_log()

        return transaction_log

    async def _take_coins(self) -> None:
        wallet_dal = AsyncWalletDAL(self.db_session)
        user_balance = await wallet_dal.get_user_balance(self.from_user.id)
        if user_balance < self.data.coins:
            raise NotEnoughCoins()
        await wallet_dal.update_by_user_id(
            self.from_user.id, {"balance": user_balance - self.data.coins}
        )

    async def _add_coins(self) -> None:
        if self.data.transaction_type == PeerTransactionENUM.purchase:
            total_coins = Decimal(self.data.coins * PURCHASE_RATE)
        elif self.data.transaction_type == PeerTransactionENUM.transfer:
            total_coins = Decimal(self.data.coins * TRANSFER_RATE)
        wallet_dal = AsyncWalletDAL(self.db_session)
        await wallet_dal.add_balance(user_id=self.to_user.id, amount=total_coins)

    async def _create_transaction_log(self):
        transaction = PeerTransaction(
            detail=self.data.detail,
            coins=self.data.coins,
            to_user_id=self.to_user.id,
            from_user_id=self.from_user.id,
            product_id=self.product.id if self.product else None,
            transaction_type=self.data.transaction_type,
        )
        transaction_log_dal = PeerTransactionDAL(self.db_session)
        return await transaction_log_dal.create(transaction)
