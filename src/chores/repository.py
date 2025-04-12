from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chores.models import Chore
from chores_completions.models import ChoreCompletion
from core.base_dals import BaseDals, DeleteDALMixin, GetOrRaiseMixin
from core.exceptions.chores import ChoreNotFoundError
from chores.schemas import ChoreCreateSchema, ChoreSchema, NewChoreDetailMax
from users.models import User


class AsyncChoreDAL(BaseDals[Chore], GetOrRaiseMixin[Chore], DeleteDALMixin[Chore]):

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

    async def get_family_chores(self, family_id: UUID) -> list[ChoreSchema] | None:
        """
        Retrieves a list of chores associated with a specific family.

        Args:
            family_id (UUID): The ID of the family whose chores are being fetched.

        Returns:
            list[ChioreSchema] | None: A list of chores if found, otherwise None.
        """
        query = select(
            Chore.id,
            Chore.name,
            Chore.description,
            Chore.icon,
            Chore.valuation,
        ).where(Chore.family_id == family_id)

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        if not raw_data:
            return None

        return [ChoreSchema.model_validate(item) for item in raw_data]

    async def get_family_chore_with_chore_completions(
        self, chore_id: UUID, limit: int, offset: int
    ) -> NewChoreDetailMax:
        """
        Fetches a family chore along with its completion details.

        Args:
            chore_id (UUID): The ID of the chore to retrieve.
            limit (int): The maximum number of chore completions to return.
            offset (int): The pagination offset.

        Returns:
            NewChoreDetailMax: The chore details with associated completions.
        """
        query = (
            select(
                Chore.id,
                Chore.name,
                Chore.description,
                Chore.icon,
                Chore.valuation,
                Chore.created_at,
                func.json_agg(
                    case(
                        (
                            ChoreCompletion.id.isnot(None),
                            func.json_build_object(
                                "id",
                                ChoreCompletion.id,
                                "completed_by",
                                func.json_build_object(
                                    "id",
                                    User.id,
                                    "username",
                                    User.username,
                                    "name",
                                    User.name,
                                    "surname",
                                    User.surname,
                                ),
                                "completed_at",
                                ChoreCompletion.created_at,
                                "status",
                                ChoreCompletion.status,
                                "message",
                                ChoreCompletion.message,
                            ),
                        ),
                        else_=None,
                    )
                ).label("chores_completion"),
            )
            .select_from(Chore)
            .join(ChoreCompletion, ChoreCompletion.chore_id == Chore.id, isouter=True)
            .join(User, User.id == ChoreCompletion.completed_by_id, isouter=True)
            .where(Chore.id == chore_id)
            .group_by(Chore.id)
            .limit(limit)
            .offset(offset)
        )

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        chores_details = NewChoreDetailMax.model_validate(raw_data[0])

        return chores_details