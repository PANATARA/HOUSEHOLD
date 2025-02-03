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
    
    async def get_family_chores(self, family_id: UUID) -> list[dict]:
        result = await self.db_session.execute(
            select(
                Chore.id.label("chore_id"),
                Chore.name.label("chore_name"),
                Chore.description.label("chore_description"),
                Chore.icon.label("chore_icon"),
                Chore.valuation.label("chore_valuation"),
            )
            .where(Chore.family_id == family_id)
        )

        rows = result.mappings().all()

        if not rows:
            return None
        return rows
