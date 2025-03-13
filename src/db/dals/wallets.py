from uuid import UUID
from decimal import Decimal

from core.base_dals import BaseUserPkDals
from sqlalchemy import exists, select, update
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

    async def deduct_balance(self, user_id: UUID, amount: Decimal) -> Decimal | None:
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
