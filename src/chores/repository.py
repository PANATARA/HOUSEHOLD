from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores.schemas import ChoreCreateSchema, ChoreResponseSchema
from core.base_dals import BaseDals, DeleteDALMixin, GetOrRaiseMixin
from core.exceptions.chores import ChoreNotFoundError


class AsyncChoreDAL(BaseDals[Chore], GetOrRaiseMixin[Chore], DeleteDALMixin):
    model = Chore
    not_found_exception = ChoreNotFoundError

    async def create_chores_many(
        self, family_id: UUID, chores_data: list[ChoreCreateSchema]
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


@dataclass
class ChoreDataService:
    db_session: AsyncSession

    async def get_family_chores(
        self, family_id: UUID, limit: int | None = None
    ) -> list[ChoreResponseSchema] | None:
        """
        Retrieves a list of chores associated with a specific family.

        Args:
            family_id (UUID): The ID of the family whose chores are being fetched.

        Returns:
            list[ChoreResponseSchema] | None: A list of chores if found, otherwise None.
        """
        query = select(
            Chore.id,
            Chore.name,
            Chore.description,
            Chore.icon,
            Chore.valuation,
        ).where(Chore.family_id == family_id, Chore.is_active)

        if limit is not None:
            query = query.limit(limit)

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        if not raw_data:
            return None

        return [ChoreResponseSchema.model_validate(item) for item in raw_data]
