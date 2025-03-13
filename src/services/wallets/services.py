from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from config.coins_settings import PURCHASE_RATE, TRANSFER_RATE
from core.constants import PeerTransactionENUM
from core.exceptions.families import UserNotFoundInFamily
from core.exceptions.wallets import NotEnoughCoins
from core.services import BaseService
from db.dals.chores import AsyncChoreDAL
from db.dals.coins_transactions import PeerTransactionDAL, RewardTransactionDAL
from db.dals.wallets import AsyncWalletDAL
from db.models.chore import ChoreCompletion
from db.models.product import Product
from db.models.user import User
from db.models.wallet import PeerTransaction, RewardTransaction, Wallet
from schemas.coins_transactions import CreatePeerTransaction, CreateRewardTransaction


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
class CoinsTransferService(BaseService):
    """
    Service for transferring coins between two users of the same family
    """
    from_user: User
    to_user: User
    count: Decimal
    message: str
    db_session: AsyncSession

    async def process(self) -> PeerTransaction | None:
        data = CreatePeerTransaction(
            detail = self.message,
            coins = self.count,
        )
        peer_transaction_service = PeerTransactionService(
            to_user = self.to_user,
            from_user = self.from_user,
            data=data,
            transaction_type=PeerTransactionENUM.transfer,
            db_session=self.db_session,
        )
        return await peer_transaction_service.run_process()


    def validate(self):
        if self.from_user.family_id != self.to_user.family_id:
            raise UserNotFoundInFamily()


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
        data = CreateRewardTransaction(
            detail = self.message,
            coins = amount,
            to_user_id =  user_id,
            chore_completion_id =  self.chore_completion.id,
        )
        transaction_log_dal = RewardTransactionDAL(self.db_session)
        return await transaction_log_dal.create_reward_for_chore_transaction(data=data)


@dataclass
class PeerTransactionService(BaseService):
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
    data: CreatePeerTransaction
    transaction_type: PeerTransactionENUM
    db_session: AsyncSession
    product: Product | None = None

    async def process(self) -> PeerTransaction | None:
        await self._take_coins()
        await self._add_coins()
        transaction_log = await self._create_transaction_log()

        return transaction_log

    async def _take_coins(self) -> None:
        wallet_dal = AsyncWalletDAL(self.db_session)
        result = await wallet_dal.deduct_balance(
            user_id=self.from_user.id, amount=self.data.coins
        )
        if result is None:
            raise NotEnoughCoins()

    async def _add_coins(self) -> None:
        if self.transaction_type == PeerTransactionENUM.purchase:
            total_coins = Decimal(self.data.coins * PURCHASE_RATE)
        elif self.transaction_type == PeerTransactionENUM.transfer:
            total_coins = Decimal(self.data.coins * TRANSFER_RATE)
        wallet_dal = AsyncWalletDAL(self.db_session)
        await wallet_dal.add_balance(user_id=self.to_user.id, amount=total_coins)

    async def _create_transaction_log(self):
        data = {
            "detail": self.data.detail,
            "coins": self.data.coins,
            "to_user_id": self.to_user.id,
            "from_user_id": self.from_user.id,
            "product_id": self.product.id if self.product else None,
            "transaction_type": self.transaction_type,
        }
        transaction_log_dal = PeerTransactionDAL(self.db_session)
        return await transaction_log_dal.create(fields=data)
    
    def validate(self):
        if self.to_user.family_id != self.from_user.family_id:
            raise UserNotFoundInFamily()