from uuid import UUID

from sqlalchemy import select

from core.base_dals import BaseDals, DeleteDALMixin, GetOrRaiseMixin
from core.exceptions.chores import ChoreNotFoundError
from db.models.chore import Chore
from schemas.chores.chores import NewChoreCreate


class AsyncChoreDAL(BaseDals[Chore], GetOrRaiseMixin[Chore], DeleteDALMixin[Chore]):

    model = Chore
    not_found_exception = ChoreNotFoundError

    async def create_chores_many(
        self, family_id: UUID, chores_data: list[NewChoreCreate]
    ) -> list[Chore]:

        chores = [
            Chore(
                name=data.name,
                description=data.description,
                icon=data.icon,
                valuation=data.valuation,
                family_id=family_id,
            )
            for data in chores_data
        ]

        self.db_session.add_all(chores)
        await self.db_session.flush()

        return chores

    async def get_chore_valutation(self, chore_id: UUID) -> int | None:
        query = select(Chore.valuation).where(Chore.id == chore_id)
        query_result = await self.db_session.execute(query)
        valutation = query_result.fetchone()
        if valutation is not None:
            return valutation[0]
        return None
