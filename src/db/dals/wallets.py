from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.user import User
from sqlalchemy import exists, select
from db.models.wallet import Wallet


@dataclass
class AsyncWalletDAL:
    db_session: AsyncSession

    async def get_wallet_user(self, user_id: UUID) -> dict:
        result = await self.db_session.execute(
            select(
                Wallet.id.label("wallet_id"),
                Wallet.balance.label("wallet_balance"),
            )
            .where(Wallet.user_id == user_id)
        )

        rows = result.mappings().first()

        if not rows:
            return None
        return rows

    async def create_wallet(self, user: UUID) -> User:
        new_wallet = Wallet(
           user_id = user
        )
        self.db_session.add(new_wallet)
        await self.db_session.flush()
        return new_wallet
    
    async def exist_wallet_user(self, user: UUID) -> bool:
        query = select(exists().where(Wallet.user_id == user))
        result = await self.db_session.execute(query)
        return result.scalar()
    
    async def delete_wallet_user(self, user: UUID) -> bool:
        return