from decimal import Decimal
from uuid import UUID
from dataclasses import dataclass

from core.base_dals import BaseDals
from db.models.chore import Chore
from sqlalchemy import select
from schemas.chores.chores import NewChoreCreate


@dataclass
class AsyncChoreDAL(BaseDals):

    class Meta:
        model = Chore

    async def create_chores_many(self, family_id: UUID, chores_data: list[NewChoreCreate]) -> list[Chore]:

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
    
    async def get_chore_valutation(self, chore_id: UUID) -> Decimal:
        query = select(Chore.valuation).where(Chore.id==chore_id)
        query_result = await self.db_session.execute(query)
        valutation = query_result.fetchone()
        return valutation[0]
