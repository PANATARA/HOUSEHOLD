from typing import Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

from db.models.chore import Chore
from db.models.family import Family
from db.models.user import User
from sqlalchemy import select

from db.models.wallet import Wallet
from schemas.chores import ChoreCreate

@dataclass
class AsyncChoreDAL:
    db_session: AsyncSession

    async def create_chores_many(self, family_id: UUID, chores_data: list[ChoreCreate]) -> list[Chore]:

        chores = [
            Chore(
                name=data.name,
                description=data.description,
                icon=data.icon,
                valuation=data.valuation,
                family_id=family_id
            )
            for data in chores_data
        ]

        self.db_session.add_all(chores)
        await self.db_session.flush()

        return chores
