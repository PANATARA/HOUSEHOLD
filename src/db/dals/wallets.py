from decimal import Decimal
from uuid import UUID

from sqlalchemy import exists, select, update

from core.base_dals import BaseUserPkDals
from db.models.wallet import Wallet


class AsyncWalletDAL(BaseUserPkDals[Wallet]):
    class Meta:
        model = Wallet

    async def exist_wallet_user(self, user: UUID) -> bool:
        query = select(exists().where(Wallet.user_id == user))
        result = await self.db_session.execute(query)
        return bool(result.scalar() or False)

    async def get_user_balance(self, user_id: UUID) -> Decimal | None:
        query = select(Wallet.balance).where(Wallet.user_id == user_id)
        result = await self.db_session.execute(query)
        balance = result.scalar()
        return Decimal(balance) if balance is not None else None

    async def add_balance(self, user_id: UUID, amount: Decimal) -> Decimal | None:
        query = (
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .values(balance=Wallet.balance + amount)
            .returning(Wallet.balance)
        )

        result = await self.db_session.execute(query)
        await self.db_session.flush()

        return result.scalar()

    async def check_and_deduct_balance(self, user_id: UUID, amount: Decimal) -> Decimal | None:
        """
        Deducts the specified amount from the user's wallet balance if sufficient funds are available.

        This method performs an atomic update to ensure that the balance does not become negative.
        If the user's balance is insufficient, the update will not be executed, and None will be returned.

        Args:
            user_id (UUID): The unique identifier of the user whose balance should be deducted.
            amount (Decimal): The amount to deduct from the user's wallet.

        Returns:
            Decimal | None: The updated balance if the deduction was successful, or None if the balance was insufficient.
        """
        query = (
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .where(Wallet.balance >= amount)
            .values(balance=Wallet.balance - amount)
            .returning(Wallet.balance)
        )

        result = await self.db_session.execute(query)
        await self.db_session.flush()

        return result.scalar()

    async def delete_wallet_user(self, user: UUID) -> None:
        return
