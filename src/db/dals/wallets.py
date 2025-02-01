from typing import Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.family import Family
from db.models.user import User
from sqlalchemy import select

from db.models.wallet import Wallet

@dataclass
class AsyncWalletDAL:
    db_session: AsyncSession

    async def create_wallet(self, user: UUID) -> User:
        new_wallet = Wallet(
           user_id = user
        )
        self.db_session.add(new_wallet)
        await self.db_session.flush()
        return new_wallet
