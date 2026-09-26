from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from chores.models import Chore, DefaultChore, DefaultChoreTranslation
from chores.schemas import (
    ChoreResponseSchema,
    DefaultChoreResponseSchema,
)
from core.base_dals import BaseDals, DeleteDALMixin
from core.exceptions.chores import ChoreNotFoundError


class ChoreRepository(BaseDals[Chore], DeleteDALMixin):
    model = Chore
    not_found_exception = ChoreNotFoundError

    async def create_chores_many(self, chores: list[Chore]) -> list[Chore]:
        self.db_session.add_all(chores)
        await self.db_session.flush()
        return chores

    async def get_family_chores(
        self, family_id: UUID, limit: int | None = None
    ) -> list[ChoreResponseSchema]:
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
            Chore.icon_color,
            Chore.icon_bg,
            Chore.valuation,
            Chore.default_chore_id,
        ).where(Chore.family_id == family_id, Chore.is_active)

        if limit is not None:
            query = query.limit(limit)

        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()

        if not raw_data:
            return []

        return [ChoreResponseSchema.model_validate(item) for item in raw_data]


class DefaultChoreRepository(BaseDals[Chore]):
    model = Chore
    not_found_exception = ChoreNotFoundError

    async def get_all_default_chores(
        self, language: str
    ) -> list[DefaultChoreResponseSchema]:
        query = (
            select(
                DefaultChore.id,
                DefaultChore.icon,
                DefaultChore.icon_color,
                DefaultChore.icon_bg,
                DefaultChore.valuation,
                DefaultChore.order,
                DefaultChoreTranslation.name,
                DefaultChoreTranslation.description,
            )
            .join(
                DefaultChoreTranslation,
                (DefaultChoreTranslation.default_chore_id == DefaultChore.id)
                & (DefaultChoreTranslation.language == language),
                isouter=True,
            )
            .where(DefaultChore.is_active)
            .order_by(DefaultChore.order)
        )
        query_result = await self.db_session.execute(query)
        raw_data = query_result.mappings().all()
        if not raw_data:
            return []
        return [DefaultChoreResponseSchema.model_validate(item) for item in raw_data]

    async def get_default_chores_not_added(
        self, family_id: UUID, language: str
    ) -> list[DefaultChoreResponseSchema]:
        query = (
            select(
                DefaultChore.id,
                DefaultChore.icon,
                DefaultChore.icon_color,
                DefaultChore.icon_bg,
                DefaultChore.valuation,
                DefaultChore.order,
                DefaultChoreTranslation.name,
                DefaultChoreTranslation.description,
            )
            .join(
                DefaultChoreTranslation,
                (DefaultChoreTranslation.default_chore_id == DefaultChore.id)
                & (DefaultChoreTranslation.language == language),
                isouter=True,
            )
            .outerjoin(
                Chore,
                (Chore.default_chore_id == DefaultChore.id)
                & (Chore.family_id == family_id),
            )
            .where(
                DefaultChore.is_active,
                Chore.id.is_(None),
            )
            .order_by(DefaultChore.order)
        )

        query_result = await self.db_session.execute(query)

        raw_data = query_result.mappings().all()

        if not raw_data:
            return []

        return [DefaultChoreResponseSchema.model_validate(item) for item in raw_data]

    async def get_by_ids_with_translations(
        self,
        ids: list[UUID],
    ) -> list[DefaultChore]:
        stmt = (
            select(DefaultChore)
            .options(selectinload(DefaultChore.translations))
            .where(
                DefaultChore.id.in_(ids),
                DefaultChore.is_active,
            )
            .order_by(DefaultChore.order)
        )
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())
